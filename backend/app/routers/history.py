"""Test Console 调用历史记录查询 API."""

from __future__ import annotations

from fastapi import APIRouter

from ..minimax_core.verification.history_store import list_history

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/test-console")
async def test_console_history(limit: int = 50) -> dict:
    """返回 Test Console 最近 N 条调用历史。"""
    items = list_history(limit=limit)
    return {"items": items}
