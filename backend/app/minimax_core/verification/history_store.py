"""Test Console 调用历史记录存储。

存储路径: backend/runtime/test_console/history.jsonl
每行一条 JSON，不做改写，只追加。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 敏感字段黑名单，不记录原始值
_SENSITIVE_KEYS = frozenset([
    "api_key", "authorization", "token", "secret",
    "password", "bearer", "x_api_key", "x_api_secret",
])

_PREVIEW_MAX_CHARS = 500


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return k in _SENSITIVE_KEYS or k.startswith("x_") or "_secret" in k


def summarize_payload(payload: dict | None) -> dict:
    """对 payload 做安全摘要，返回不含敏感信息的概要。"""
    if payload is None:
        return {"payload_keys": [], "payload_size_chars": 0, "payload_preview": ""}

    keys = list(payload.keys())
    size_chars = sum(len(str(v)) for v in payload.values())
    # 构建预览，只截取前 _PREVIEW_MAX_CHARS
    safe_pairs = [
        f'"{k}":"[REDACTED]"' if _is_sensitive_key(k) else f'"{k}":{json.dumps(str(v)[:200], ensure_ascii=False)}'
        for k, v in list(payload.items())[:20]
    ]
    preview = "{" + ",".join(safe_pairs) + "}"
    if len(preview) > _PREVIEW_MAX_CHARS:
        preview = preview[:_PREVIEW_MAX_CHARS] + "..."

    return {
        "payload_keys": [k for k in keys if not _is_sensitive_key(k)],
        "payload_size_chars": size_chars,
        "payload_preview": preview,
    }


def append_history(
    action: str,
    capability_id: str,
    payload: dict | None,
    confirmations: dict | None,
    result: dict,
) -> None:
    """追加一条历史记录到 JSONL 文件。写失败不抛异常。"""
    try:
        record = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "capability_id": capability_id,
            "payload_summary": summarize_payload(payload),
            "confirmations": confirmations or {},
            "result": result,
        }
        _ensure_dir().joinpath("history.jsonl").append_text(
            json.dumps(record, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception:
        # 写失败不影响主流程，吞掉
        pass


def list_history(limit: int = 50) -> list[dict]:
    """读取最近 N 条历史记录，返回列表（最新优先）。"""
    path = _ensure_dir().joinpath("history.jsonl")
    if not path.exists():
        return []

    lines: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    records = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            continue
        if len(records) >= limit:
            break
    return records


def _ensure_dir() -> Path:
    d = Path(__file__).resolve().parent.parent.parent.parent / "runtime" / "test_console"
    d.mkdir(parents=True, exist_ok=True)
    return d
