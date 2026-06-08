"""Test Console 调用历史记录存储。

存储路径: backend/runtime/test_console/history.jsonl
每行一条 JSON，不做改写，只追加。
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .diagnostics_store import append_trace_event
except ImportError:
    append_trace_event = None  # type: ignore

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


# ── Asset extraction helpers ──────────────────────────────────────────

_IMG_EXT_RELS = frozenset({"jpg", "jpeg", "png", "webp", "gif", "bmp", "svg"})
_AUD_EXT_RELS = frozenset({"mp3", "wav", "m4a", "flac", "ogg", "aac"})

# Fields whose values are semantically image/audio URLs — skip extension check
_STRONG_IMG_URL_FIELDS = frozenset({
    "image_url", "img_url", "imageUrl", "imageURL",
    "image_file",
})
_STRONG_AUD_URL_FIELDS = frozenset({
    "audio_url", "voice_url", "speech_url", "music_url",
})
_STRONG_URL_FIELDS = _STRONG_IMG_URL_FIELDS | _STRONG_AUD_URL_FIELDS

# Generic URL fields that need weak inference (extension + keyword heuristics)
_WEAK_URL_FIELDS = frozenset({"file_url", "download_url", "url", "content_url"})

_AUDIO_KW = frozenset({"audio", "music", "voice", "speech", "sound", "song", "tts", "asr"})
_IMAGE_KW = frozenset({"image", "img", "picture", "photo", "pic", "thumbnail"})

_URL_MAX_LEN = 500
_TEXT_PREVIEW_MAX = 300
_ASSETS_MAX = 10
_SUMMARIZE_DEPTH = 4

# ── result record summarization (for history.jsonl result field) ─────────

_RESULT_RECORD_MAX_ERROR = 300
_RESULT_RECORD_LIST_MAX = 10
_RESULT_RECORD_ITEM_MAX = 200


def _safe_list(items: list, max_items: int, max_item_len: int) -> list:
    """Truncate a list to max_items, each item to max_item_len chars."""
    return [
        str(item)[:max_item_len] + ("…" if len(str(item)) > max_item_len else "")
        for item in items[:max_items]
    ]


def summarize_result_record(result: Any) -> dict:
    """Extract a compact status record for storage in history.jsonl 'result' field.

    Output is a small dict with only status fields — no data, raw, base_resp,
    or model output. Designed to prevent history.jsonl bloat.

    Output fields:
      - ok: bool | None
      - allowed: None (always)
      - error: str | None (max 300 chars)
      - status: str | None
      - message: str | None (max 300 chars)
      - blocked_reasons: list[str] (max 10 items, each max 200 chars)
      - required_confirmations: list[str] (max 10 items, each max 200 chars)
      - warnings: list[str] (max 10 items, each max 200 chars)
    """
    if result is None:
        return {
            "ok": None,
            "allowed": None,
            "error": None,
            "status": None,
            "message": None,
            "blocked_reasons": [],
            "required_confirmations": [],
            "warnings": [],
        }

    if not isinstance(result, dict):
        return {
            "ok": None,
            "allowed": None,
            "error": str(result)[:_RESULT_RECORD_MAX_ERROR] if len(str(result)) > _RESULT_RECORD_MAX_ERROR else str(result),
            "status": None,
            "message": None,
            "blocked_reasons": [],
            "required_confirmations": [],
            "warnings": [],
        }

    ok_val = result.get("ok", result.get("allowed"))

    # error
    error_val = result.get("error")
    if error_val:
        error_str = str(error_val)
        if len(error_str) > _RESULT_RECORD_MAX_ERROR:
            error_str = error_str[:_RESULT_RECORD_MAX_ERROR] + "…"
    else:
        error_str = None

    # message
    message_val = result.get("message")
    if message_val:
        msg_str = str(message_val)
        if len(msg_str) > _RESULT_RECORD_MAX_ERROR:
            msg_str = msg_str[:_RESULT_RECORD_MAX_ERROR] + "…"
    else:
        msg_str = None

    # status
    status_val = result.get("status")
    if status_val:
        status_val = str(status_val)[:_RESULT_RECORD_MAX_ERROR]

    # blocked_reasons
    blocked_reasons = []
    if "blocked_reasons" in result and isinstance(result["blocked_reasons"], list):
        blocked_reasons = _safe_list(
            result["blocked_reasons"],
            _RESULT_RECORD_LIST_MAX,
            _RESULT_RECORD_ITEM_MAX,
        )

    # required_confirmations
    required_confirmations = []
    if "required_confirmations" in result and isinstance(result["required_confirmations"], list):
        required_confirmations = _safe_list(
            result["required_confirmations"],
            _RESULT_RECORD_LIST_MAX,
            _RESULT_RECORD_ITEM_MAX,
        )

    # warnings
    warnings = []
    if "warnings" in result and isinstance(result["warnings"], list):
        warnings = _safe_list(
            result["warnings"],
            _RESULT_RECORD_LIST_MAX,
            _RESULT_RECORD_ITEM_MAX,
        )

    return {
        "ok": bool(ok_val) if ok_val is not None else None,
        "allowed": None,
        "error": error_str,
        "status": status_val,
        "message": msg_str,
        "blocked_reasons": blocked_reasons,
        "required_confirmations": required_confirmations,
        "warnings": warnings,
    }


def _url_ext(url: str) -> str | None:
    """Return lowercased file extension from URL path, without query/fragment."""
    import re
    m = re.search(r"\.([a-zA-Z0-9]+)(?:\?|#|$)", url)
    return m.group(1).lower() if m else None


def _is_image_url(url: str, field_name: str = "") -> bool:
    if field_name in _STRONG_IMG_URL_FIELDS:
        return True
    ext = _url_ext(url)
    return ext in _IMG_EXT_RELS if ext else False


def _is_audio_url(url: str, field_name: str = "") -> bool:
    if field_name in _STRONG_AUD_URL_FIELDS:
        return True
    ext = _url_ext(url)
    return ext in _AUD_EXT_RELS if ext else False


def _url_type_hint(url: str, field_name: str) -> str | None:
    """Infer asset type for weak URL fields (file_url, download_url, url, content_url).

    Returns: "image" | "audio" | "file" | None
    """
    # 1. Check URL extension first
    ext = _url_ext(url)
    if ext:
        if ext in _AUD_EXT_RELS:
            return "audio"
        if ext in _IMG_EXT_RELS:
            return "image"
    # 2. Check keywords in field name and URL
    combined = (field_name + " " + url).lower()
    has_audio = any(kw in combined for kw in _AUDIO_KW)
    has_image = any(kw in combined for kw in _IMAGE_KW)
    if has_audio and not has_image:
        return "audio"
    if has_image and not has_audio:
        return "image"
    # 3. Default to file
    return "file"


def _safe_str(value: Any, max_len: int) -> str:
    s = str(value)
    return s[:max_len] + ("…" if len(s) > max_len else "")


def summarize_result(result: Any) -> dict:
    """Extract a safe, compact summary from an invoke/risk-check result.

    Returns a dict with:
      - ok / error / message
      - output_type (image | audio | text | file | json | unknown)
      - asset_count
      - assets: up to 10 asset entries { type, url, label, file_id, filename, mime_type, content_length }
      - text_preview: short text excerpt (max 300 chars)
      - raw_keys: top-level non-sensitive keys present

    Security: sensitive keys (api_key, token, authorization, etc.) and large
    payloads are redacted / truncated. Never writes raw values of sensitive fields.
    """
    if result is None:
        return {"ok": None, "output_type": "unknown", "asset_count": 0, "assets": [], "raw_keys": []}

    if not isinstance(result, dict):
        return {"ok": None, "output_type": "unknown", "asset_count": 0, "assets": [], "raw_keys": []}

    out: dict[str, Any] = {
        "ok": result.get("ok", result.get("allowed")),
        "error": None,
        "message": None,
        "output_type": "unknown",
        "asset_count": 0,
        "assets": [],
        "text_preview": None,
        "raw_keys": [],
    }

    # Error / message extraction
    if not out["ok"]:
        out["error"] = _safe_str(result.get("error") or "", 100)
        out["message"] = _safe_str(result.get("message") or "", 200)
    # raw_keys: collect non-sensitive top-level keys first, then override with data keys
    out["raw_keys"] = [k for k in result.keys() if not _is_sensitive_key(k)]
    if "data" in result and isinstance(result["data"], dict):
        out["raw_keys"] = [k for k in result["data"].keys() if not _is_sensitive_key(k)]

    # Collect assets recursively
    assets: list[dict] = []
    _collect_assets(result, depth=0, assets=assets)
    out["assets"] = assets[:_ASSETS_MAX]
    out["asset_count"] = len(assets)

    # Determine output_type from assets
    if assets:
        first_type = assets[0].get("type", "unknown")
        if first_type in ("image", "audio", "file"):
            out["output_type"] = first_type
        else:
            out["output_type"] = "unknown"

    # Text preview: look for common text fields
    for field in ("lyrics", "text", "content", "answer", "message"):
        if field in result and isinstance(result[field], str) and result[field].strip():
            out["text_preview"] = _safe_str(result[field], _TEXT_PREVIEW_MAX)
            if out["output_type"] == "unknown":
                out["output_type"] = "text"
            break
        # Also check nested data.*
        d = result.get("data")
        if isinstance(d, dict) and field in d and isinstance(d[field], str) and d[field].strip():
            out["text_preview"] = _safe_str(d[field], _TEXT_PREVIEW_MAX)
            if out["output_type"] == "unknown":
                out["output_type"] = "text"
            break

    return out


def _collect_assets(data: Any, depth: int, assets: list[dict]) -> None:
    """Recursively collect image/audio/file assets into assets list (max 20 collected)."""
    if depth > _SUMMARIZE_DEPTH or len(assets) >= 20:
        return
    if data is None:
        return
    if isinstance(data, dict):
        d = data
        # file_id fields → file asset
        if "file_id" in d and isinstance(d["file_id"], str) and d["file_id"].strip():
            assets.append({
                "type": "file",
                "url": None,
                "label": _safe_str(d["file_id"], 80),
                "file_id": _safe_str(d["file_id"], 80),
                "filename": _safe_str(d.get("filename", ""), 120) or None,
                "mime_type": str(d.get("mime_type", "")) or None,
                "content_length": int(d["content_length"]) if "content_length" in d and str(d["content_length"]).isdigit() else None,
            })
            return  # file_id is terminal, don't recurse further

        # URL-like string fields — strong typed first, then weak inference
        for field in ("image_url", "img_url", "imageUrl", "imageURL", "image_file",
                      "audio_url", "voice_url", "speech_url", "music_url"):
            if field in d and isinstance(d[field], str) and d[field].strip():
                url = d[field]
                if not (url.startswith("http://") or url.startswith("https://")):
                    continue
                truncated = url[:_URL_MAX_LEN] + ("…" if len(url) > _URL_MAX_LEN else "")
                if _is_image_url(url, field):
                    assets.append({"type": "image", "url": truncated, "label": field, "file_id": None, "filename": None, "mime_type": None, "content_length": None})
                elif _is_audio_url(url, field):
                    assets.append({"type": "audio", "url": truncated, "label": field, "file_id": None, "filename": None, "mime_type": None, "content_length": None})
                # Continue checking other fields — don't return here

        # Weak URL fields — use extension + keyword heuristics
        for field in ("file_url", "download_url", "url", "content_url"):
            if field in d and isinstance(d[field], str) and d[field].strip():
                url = d[field]
                if not (url.startswith("http://") or url.startswith("https://")):
                    continue
                truncated = url[:_URL_MAX_LEN] + ("…" if len(url) > _URL_MAX_LEN else "")
                type_hint = _url_type_hint(url, field)
                if type_hint == "file":
                    assets.append({"type": "file", "url": truncated, "label": field, "file_id": None, "filename": None, "mime_type": None, "content_length": None})
                elif type_hint == "image":
                    assets.append({"type": "image", "url": truncated, "label": field, "file_id": None, "filename": None, "mime_type": None, "content_length": None})
                elif type_hint == "audio":
                    assets.append({"type": "audio", "url": truncated, "label": field, "file_id": None, "filename": None, "mime_type": None, "content_length": None})
                # Continue checking other fields — don't return here

        # Recurse into nested containers and arrays
        for key in ("data", "result", "output", "response", "body", "content"):
            if key in d and isinstance(d[key], (dict, list)):
                _collect_assets(d[key], depth + 1, assets)
                if len(assets) >= 20:
                    return
        for key, val in d.items():
            if key in ("data", "result", "output", "response", "body", "content"):
                continue  # already handled above
            if isinstance(val, list):
                for item in val[:10]:
                    _collect_assets(item, depth + 1, assets)
                    if len(assets) >= 20:
                        return
    elif isinstance(data, list):
        for item in data[:10]:
            _collect_assets(item, depth + 1, assets)
            if len(assets) >= 20:
                return


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
    duration_ms: int | None = None,
    trace_id: str | None = None,
) -> str | None:
    """追加一条历史记录到 JSONL 文件。写失败不抛异常。

    Args:
        trace_id: optional trace ID for observability chain tracking.

    Returns:
        The record ID on success, None on failure.
    """
    if append_trace_event and trace_id:
        append_trace_event(
            trace_id,
            "history_append_attempt",
            capability_id=capability_id,
            action=action,
            data={"history_path": "runtime/test_console/history.jsonl"},
        )

    try:
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "capability_id": capability_id,
            "duration_ms": duration_ms,
            "trace_id": trace_id,
            "payload_summary": summarize_payload(payload),
            "confirmations": confirmations or {},
            "result": summarize_result_record(result),
            "result_summary": summarize_result(result),
        }
        path = _ensure_dir().joinpath("history.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        compact_history_if_needed()

        if append_trace_event and trace_id:
            append_trace_event(
                trace_id,
                "history_append_success",
                capability_id=capability_id,
                action=action,
                data={
                    "history_id": record_id,
                    "history_path": "runtime/test_console/history.jsonl",
                },
            )

        return record_id
    except Exception as e:
        # 写失败不影响主流程，吞掉
        import sys
        import traceback
        print(f"[history] append failed: {e}", file=sys.stderr)
        traceback.print_exc()

        if append_trace_event and trace_id:
            append_trace_event(
                trace_id,
                "history_append_failed",
                capability_id=capability_id,
                action=action,
                status="error",
                message=str(e),
            )

        return None


def list_history(limit: int = _DEFAULT_HISTORY_LIMIT, capability_id: str | None = None) -> list[dict]:
    """读取最近 N 条历史记录，返回列表（最新优先）。

    Args:
        limit: 最大返回条数，默认 50，最大 200
        capability_id: 可选，按 capability_id 过滤（支持 risk_check 和 invoke 两类）
    """
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
    # 如果指定了 capability_id，先收集够足够多的记录再过滤。
    records = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except Exception:
            continue
        # capability_id 过滤
        if capability_id and record.get("capability_id") != capability_id:
            continue
        records.append(record)
        if len(records) >= safe_limit:
            break
    return records


def _ensure_dir() -> Path:
    override = os.environ.get("MINIMAX_HISTORY_DIR")
    if override:
        d = Path(override)
    else:
        d = Path(__file__).resolve().parent.parent.parent.parent / "runtime" / "test_console"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_history_status() -> dict:
    """Return history file status without exposing absolute server paths.

    Returns:
        dict with history_path (relative), exists, line_count, valid_record_count,
        size_bytes, last_modified (ISO string or null), history_dir_exists, history_file_name.
    """
    # Use a logical relative path, not absolute filesystem path
    history_rel_path = "runtime/test_console/history.jsonl"
    parent_dir = _ensure_dir()
    path = parent_dir.joinpath("history.jsonl")

    result: dict = {
        "history_path": history_rel_path,
        "history_dir_exists": parent_dir.exists(),
        "history_file_name": "history.jsonl",
        "exists": False,
        "line_count": 0,
        "valid_record_count": 0,
        "size_bytes": 0,
        "last_modified": None,
    }

    if path.exists():
        try:
            stat = path.stat()
            result["size_bytes"] = stat.st_size
            result["last_modified"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            result["exists"] = True

            with open(path, encoding="utf-8") as f:
                lines = f.readlines()

            non_empty_lines = [l for l in lines if l.strip()]
            result["line_count"] = len(non_empty_lines)

            # Count lines that are valid JSON (valid_record_count)
            valid_count = 0
            for line in non_empty_lines:
                try:
                    json.loads(line)
                    valid_count += 1
                except Exception:
                    pass
            result["valid_record_count"] = valid_count
        except Exception:
            pass

    return result
