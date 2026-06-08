"""统一调用入口。所有已实现 capability 都通过 POST /api/invoke/<id> 触发，
前端只关心 capability id 和 payload，不关心上游具体路径。

这样：
- 前端代码量恒定，新能力只需 register_handler
- 鉴权、错误归一化、未实现拦截只写一次
- RiskGate 门禁：所有能力执行前必须通过风险评估
"""
from __future__ import annotations

import time
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..minimax.client import MiniMaxError
from ..minimax_core.guards.risk_gate import evaluate_capability_risk
from ..registry import HANDLERS, get_registry
from ..minimax_core.registry.loader import get_capability_registry
from ..minimax_core.verification.history_store import append_history

router = APIRouter(prefix="/invoke", tags=["invoke"])


class InvokeRequest(BaseModel):
    payload: dict | None = None
    confirmations: dict | None = None


def _extract_base_resp_error(result: object) -> dict | None:
    """从 MiniMax handler 返回值中提取 base_resp 业务错误。

    MiniMax API 在业务层面失败时会返回：
      {"base_resp": {"status_code": 2013, "status_msg": "invalid params, empty field"}}

    status_code == 0 表示成功，非 0 都是业务错误。
    """
    if not isinstance(result, dict):
        return None
    base_resp = result.get("base_resp")
    if not isinstance(base_resp, dict):
        return None
    status_code = base_resp.get("status_code")
    try:
        code = int(status_code)
    except (TypeError, ValueError):
        return None
    if code == 0:
        return None
    return {
        "error": "minimax_business_error",
        "status": code,
        "message": str(base_resp.get("status_msg") or "MiniMax business error"),
    }


def _append_invoke_history(
    action: str,
    cap_id: str,
    payload: dict,
    confirmations: dict,
    result: dict,
    t0: float,
) -> str | None:
    """追加历史记录，返回 record ID（供前端调试观测）。"""
    duration_ms = int((time.perf_counter() - t0) * 1000)
    return append_history(
        action=action,
        capability_id=cap_id,
        payload=payload,
        confirmations=confirmations,
        result=result,
        duration_ms=duration_ms,
    )


@router.post("/{cap_id}")
async def invoke(cap_id: str, body: InvokeRequest | None = None) -> JSONResponse:
    payload = body.payload if body else None
    confirmations = body.confirmations if body else None
    payload = payload or {}
    confirmations = confirmations or {}

    reg = get_registry()
    cap = next((c for c in reg.capabilities if c.id == cap_id), None)
    if cap is None:
        raise HTTPException(404, f"unknown capability: {cap_id}")
    if cap.status == "unsupported":
        raise HTTPException(403, f"capability {cap_id} 在当前订阅档位下不可用")
    if cap.multipart:
        raise HTTPException(
            400,
            f"capability {cap_id} 是 multipart 上传，请走 POST /api/upload/{cap_id}",
        )
    handler = HANDLERS.get(cap_id)
    if handler is None:
        raise HTTPException(501, f"capability {cap_id} 尚未实现 handler")

    t0 = time.perf_counter()

    # RiskGate 评估
    caps = get_capability_registry()
    core_cap = caps.by_id(cap_id)
    if core_cap is not None:
        decision = evaluate_capability_risk(core_cap, confirmations=confirmations, payload=payload)
        if not decision.allowed:
            content = {
                "error": "risk_gate_blocked",
                "message": (
                    f"Capability '{cap.label}' requires explicit confirmation before execution. "
                    f"Required: {decision.required_confirmations}. "
                    f"Reasons: {'; '.join(decision.blocked_reasons)}"
                ),
                "blocked_reasons": decision.blocked_reasons,
                "required_confirmations": decision.required_confirmations,
                "warnings": decision.warnings,
            }
            history_id = _append_invoke_history(
                "invoke", cap_id, payload, confirmations,
                {"ok": False, "allowed": False, **content}, t0,
            )
            if history_id:
                content["history_id"] = history_id
            return JSONResponse(status_code=403, content=content)

    try:
        result = await handler(payload)
    except MiniMaxError as e:
        content = {"error": "minimax_error", "status": e.status, "message": e.message}
        history_id = _append_invoke_history(
            "invoke", cap_id, payload, confirmations,
            {"ok": False, "error": "minimax_error", "status": e.status, "message": e.message}, t0,
        )
        if history_id:
            content["history_id"] = history_id
        return JSONResponse(
            status_code=502 if e.status >= 500 else e.status,
            content=content,
        )

    # 检查 MiniMax 业务层错误（如 base_resp.status_code != 0）
    business_error = _extract_base_resp_error(result)
    if business_error:
        history_id = _append_invoke_history(
            "invoke", cap_id, payload, confirmations,
            {"ok": False, **business_error, "data": result}, t0,
        )
        content = {**business_error, "data": result}
        if history_id:
            content["history_id"] = history_id
        return JSONResponse(status_code=400, content=content)

    # 真正成功
    history_id = _append_invoke_history(
        "invoke", cap_id, payload, confirmations,
        {"ok": True, "data": result}, t0,
    )
    content = {"ok": True, "data": result}
    if history_id:
        content["history_id"] = history_id
    return JSONResponse(content=content)
