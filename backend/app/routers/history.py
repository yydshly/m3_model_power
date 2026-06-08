"""Test Console 调用历史记录查询 API."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..minimax_core.verification.diagnostics_store import new_trace_id, append_trace_event
from ..minimax_core.verification.history_store import append_history, list_history, normalize_limit, get_history_status

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/status")
async def history_status() -> dict:
    """返回 history 文件的状态信息，不含任何 payload 原文或密钥。"""
    return get_history_status()


@router.get("/test-console")
async def test_console_history(limit: int = 50) -> dict:
    """返回 Test Console 最近 N 条调用历史（最多 200 条）。"""
    safe_limit = normalize_limit(limit)
    items = list_history(limit=safe_limit)
    return {"items": items}


@router.get("/capability/{capability_id}")
async def capability_history(capability_id: str, limit: int = 50) -> dict:
    """返回指定能力最近的 N 条调用历史（最多 200 条）。

    同时返回 risk_check 和 invoke 两类记录，按时间倒序。
    """
    safe_limit = normalize_limit(limit)
    items = list_history(limit=safe_limit, capability_id=capability_id)
    return {"items": items}


class HistoryProbeRequest(BaseModel):
    capability_id: str = "history-probe"
    action: str = "diagnostic_probe"


@router.post("/probe")
async def history_probe(req: HistoryProbeRequest, request: Request) -> dict:
    """写入一条诊断历史记录，验证当前运行后端的 history 写入能力。

    不调用 MiniMax，仅验证后端能否成功写入 history.jsonl。
    """
    trace_id = getattr(request.state, "trace_id", None) or new_trace_id("probe")

    append_trace_event(
        trace_id,
        "history_probe_started",
        capability_id=req.capability_id,
        action=req.action,
    )

    history_id = append_history(
        action=req.action,
        capability_id=req.capability_id,
        payload={"probe": True},
        confirmations={},
        result={"ok": True, "data": {"probe": True}},
        duration_ms=0,
        trace_id=trace_id,
    )

    return {
        "ok": bool(history_id),
        "trace_id": trace_id,
        "history_id": history_id,
    }
