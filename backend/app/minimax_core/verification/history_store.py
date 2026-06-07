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


# ── Asset extraction helpers ──────────────────────────────────────────

_IMG_EXT_RELS = frozenset({"jpg", "jpeg", "png", "webp", "gif", "bmp", "svg"})
_AUD_EXT_RELS = frozenset({"mp3", "wav", "m4a", "flac", "ogg", "aac"})

# Fields whose values are semantically image/audio URLs — skip extension check
_STRONG_IMG_URL_FIELDS = frozenset({
    "image_url", "img_url", "imageUrl", "imageURL",
    "file_url", "download_url", "image_file",
})
_STRONG_AUD_URL_FIELDS = frozenset({
    "audio_url", "voice_url", "speech_url", "music_url",
})
_STRONG_URL_FIELDS = _STRONG_IMG_URL_FIELDS | _STRONG_AUD_URL_FIELDS

_URL_MAX_LEN = 500
_TEXT_PREVIEW_MAX = 300
_ASSETS_MAX = 10
_SUMMARIZE_DEPTH = 4


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

        # URL-like string fields
        for field in ("image_url", "img_url", "imageUrl", "imageURL",
                      "file_url", "download_url", "image_file",
                      "audio_url", "voice_url", "speech_url", "music_url",
                      "url", "audio", "content_url"):
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
            "result_summary": summarize_result(result),
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
