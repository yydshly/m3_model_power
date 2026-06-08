"""Diagnostics trace store — records trace events for history chain observability.

写入路径: backend/runtime/diagnostics/trace.jsonl
每行一条 JSON，不记录 token、headers、完整 payload、完整模型输出。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def new_trace_id(prefix: str = "hist") -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def _diag_dir() -> Path:
    override = os.environ.get("MINIMAX_DIAGNOSTICS_DIR")
    if override:
        d = Path(override)
    else:
        d = Path(__file__).resolve().parent.parent.parent.parent / "runtime" / "diagnostics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def append_trace_event(
    trace_id: str | None,
    event: str,
    *,
    capability_id: str | None = None,
    action: str | None = None,
    status: str = "ok",
    message: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Append a trace event to runtime/diagnostics/trace.jsonl.

    Does nothing if trace_id is None/empty.
    Does NOT record tokens, headers, full payloads, or full model outputs.
    """
    if not trace_id:
        return

    record = {
        "trace_id": trace_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "capability_id": capability_id,
        "action": action,
        "status": status,
        "message": message,
        "data": data or {},
    }

    path = _diag_dir() / "trace.jsonl"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # diagnostics failures never crash the main path
        pass


def list_trace_events(trace_id: str, limit: int = 100) -> list[dict]:
    """Return trace events for the given trace_id, newest-last, up to limit."""
    path = _diag_dir() / "trace.jsonl"
    if not path.exists():
        return []

    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in reversed(f.readlines()):
            try:
                item = json.loads(line)
            except Exception:
                continue
            if item.get("trace_id") == trace_id:
                out.append(item)
            if len(out) >= limit:
                break
    return list(reversed(out))


def get_diagnostics_status() -> dict:
    """Return diagnostics file status without exposing absolute server paths."""
    path = _diag_dir() / "trace.jsonl"
    return {
        "diagnostics_path": "runtime/diagnostics/trace.jsonl",
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
