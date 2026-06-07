"""统一调用入口。所有已实现 capability 都通过 POST /api/invoke/<id> 触发，
前端只关心 capability id 和 payload，不关心上游具体路径。

这样：
- 前端代码量恒定，新能力只需 register_handler
- 鉴权、错误归一化、未实现拦截只写一次
- RiskGate 门禁：所有能力执行前必须通过风险评估
"""
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
            append_history(
                action="invoke",
                capability_id=cap_id,
                payload=payload,
                confirmations=confirmations,
                result={"ok": False, "allowed": False, **content},
            )
            return JSONResponse(status_code=403, content=content)

    try:
        result = await handler(payload)
    except MiniMaxError as e:
        content = {"error": "minimax_error", "status": e.status, "message": e.message}
        append_history(
            action="invoke",
            capability_id=cap_id,
            payload=payload,
            confirmations=confirmations,
            result={"ok": False, "error": "minimax_error", "status": e.status, "message": e.message},
        )
        return JSONResponse(
            status_code=502 if e.status >= 500 else e.status,
            content=content,
        )
    content = {"ok": True, "data": result}
    append_history(
        action="invoke",
        capability_id=cap_id,
        payload=payload,
        confirmations=confirmations,
        result={"ok": True},
    )
    return JSONResponse(content=content)
