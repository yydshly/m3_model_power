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

# ── Constants ─────────────────────────────────────────────────────────

_HISTORY_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_HISTORY_KEEP_LINES = 1000
_DEFAULT_HISTORY_LIMIT = 50
_MAX_HISTORY_LIMIT = 200
_PREVIEW_MAX_CHARS = 500
_MAX_RECURSION_DEPTH = 3
_MAX_LIST_ITEMS = 10
_MAX_STR_CHARS = 200

# ── Sensitive key detection ────────────────────────────────────────────

_SENSITIVE_KEYS = frozenset([
    # Exact matches
    "api_key", "authorization", "token", "secret",
    "password", "bearer", "x_api_key", "x_api_secret",
    "access_token", "refresh_token", "id_token",
    "client_secret", "private_key", "jwt",
    "cookie", "set_cookie", "session", "session_id",
])

# Substrings that trigger redaction (case-insensitive checked on key.lower())
_SENSITIVE_SUBSTRINGS = frozenset([
    "secret", "token", "password", "authorization",
    "cookie", "session", "private", "jwt",
])


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    if k in _SENSITIVE_KEYS:
        return True
    if any(sub in k for sub in _SENSITIVE_SUBSTRINGS):
        return True
    if k.startswith("x_"):
        return True
    return False


# ── Recursive redaction ────────────────────────────────────────────────

def redact_value(value: Any, depth: int = 0) -> Any:
    """递归脱敏 value，超过深度限制返回截断标记。"""
    if depth > _MAX_RECURSION_DEPTH:
        return "[TRUNCATED_DEPTH]"

    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if _is_sensitive_key(k) else redact_value(v, depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            redact_value(item, depth + 1)
            for item in value[:_MAX_LIST_ITEMS]
        ]
    if isinstance(value, str):
        return value[:_MAX_STR_CHARS]
    return value


def summarize_payload(payload: dict | None) -> dict:
    """对 payload 做安全摘要，返回不含敏感信息的概要。"""
    if payload is None:
        return {"payload_keys": [], "payload_size_chars": 0, "payload_preview": ""}

    # 递归脱敏后再构建预览
    safe_payload = redact_value(payload)
    safe_str = json.dumps(safe_payload, ensure_ascii=False)
    preview = safe_str[:_PREVIEW_MAX_CHARS]
    if len(safe_str) > _PREVIEW_MAX_CHARS:
        preview += "..."

    keys = [k for k in payload.keys() if not _is_sensitive_key(k)]
    size_chars = sum(len(str(v)) for v in payload.values())

    return {
        "payload_keys": keys,
        "payload_size_chars": size_chars,
        "payload_preview": preview,
    }


# ── History file management ────────────────────────────────────────────

def normalize_limit(limit: int | None, *, default: int = _DEFAULT_HISTORY_LIMIT, max_limit: int = _MAX_HISTORY_LIMIT) -> int:
    """将 limit 参数规整到合法区间。"""
    if limit is None:
        return default
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return default
    if n < 1:
        return 1
    if n > max_limit:
        return max_limit
    return n


def compact_history_if_needed() -> None:
    """如果 history.jsonl 超过 _HISTORY_MAX_BYTES，只保留最后 _HISTORY_KEEP_LINES 行。"""
    try:
        path = _ensure_dir().joinpath("history.jsonl")
        if not path.exists():
            return
        if path.stat().st_size < _HISTORY_MAX_BYTES:
            return

        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) <= _HISTORY_KEEP_LINES:
            return

        # 只保留最后 _HISTORY_KEEP_LINES 行
        trimmed = lines[-_HISTORY_KEEP_LINES:]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(trimmed)
    except Exception:
        # compact 失败不影响主流程
        pass


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
        path = _ensure_dir().joinpath("history.jsonl")
        path.append_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
        compact_history_if_needed()
    except Exception:
        # 写失败不影响主流程，吞掉
        pass


def list_history(limit: int = _DEFAULT_HISTORY_LIMIT) -> list[dict]:
    """读取最近 N 条历史记录，返回列表（最新优先）。"""
    safe_limit = normalize_limit(limit)
    path = _ensure_dir().joinpath("history.jsonl")
    if not path.exists():
        return []

    lines: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    # history 文件会在 append 时 compact 到有限大小；这里读取全量文件后反向取最近 safe_limit 条。
    records = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            continue
        if len(records) >= safe_limit:
            break
    return records


def _ensure_dir() -> Path:
    d = Path(__file__).resolve().parent.parent.parent.parent / "runtime" / "test_console"
    d.mkdir(parents=True, exist_ok=True)
    return d
