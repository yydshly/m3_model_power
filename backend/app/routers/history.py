"""Test Console 调用历史记录查询 API."""

from __future__ import annotations

from fastapi import APIRouter

from ..minimax_core.verification.history_store import list_history, normalize_limit, get_history_status

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
