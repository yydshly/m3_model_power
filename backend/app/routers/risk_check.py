"""RiskGate 检查端点 —— 不调用 MiniMax API，只做门禁评估。

POST /api/capabilities/{cap_id}/risk-check
Body: { payload?: {}, confirmations?: {} }
Response: { allowed: bool, blocked_reasons: string[], required_confirmations: string[], warnings: string[] }
"""
from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from ..minimax_core.guards.risk_gate import evaluate_capability_risk
from ..minimax_core.registry.loader import get_capability_registry
from ..minimax_core.verification.history_store import append_history

router = APIRouter(prefix="/capabilities", tags=["risk-check"])


class RiskCheckRequest(BaseModel):
    payload: dict | None = None
    confirmations: dict | None = None


@router.post("/{cap_id}/risk-check")
async def risk_check(cap_id: str, body: RiskCheckRequest) -> dict:
    """对指定能力做 RiskGate 评估，不调用 MiniMax API。

    用于前端在正式调用前先做门禁预检。
    """
    caps = get_capability_registry()
    cap = caps.by_id(cap_id)
    if cap is None:
        raise HTTPException(404, f"unknown capability: {cap_id}")

    decision = evaluate_capability_risk(
        cap,
        confirmations=body.confirmations or {},
        payload=body.payload or {},
    )
    result = decision.to_dict()
    append_history(
        action="risk_check",
        capability_id=cap_id,
        payload=body.payload,
        confirmations=body.confirmations,
        result=result,
    )
    return result
