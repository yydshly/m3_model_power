"""Test Console 调用历史记录查询 API."""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter

from ..minimax_core.verification.history_store import list_history, normalize_limit, _ensure_dir

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/status")
async def history_status() -> dict:
    """返回 history 文件的状态信息，不含任何 payload 原文或密钥。"""
    path = _ensure_dir().joinpath("history.jsonl")
    result: dict = {
        "history_path": str(path),
        "exists": path.exists(),
        "record_count": 0,
        "size_bytes": 0,
        "last_modified": None,
    }
    if path.exists():
        try:
            stat = path.stat()
            result["size_bytes"] = stat.st_size
            mtime = stat.st_mtime
            result["last_modified"] = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            # Count lines without reading full content
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            result["record_count"] = len([l for l in lines if l.strip()])
        except Exception:
            pass
    return result


@router.get("/test-console")
async def test_console_history(limit: int = 50) -> dict:
    """返回 Test Console 最近 N 条调用历史（最多 200 条）。"""
    safe_limit = normalize_limit(limit)
    items = list_history(limit=safe_limit)
    return {"items": items}
