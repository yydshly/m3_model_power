"""rebuild_verification_index.py

从已有验收记录（latest.json / probe reports / Matrix doc）中回填聚合索引，
生成：
  - backend/runtime/capability_verification/all_verified.json   （本地，不提交 Git）
  - docs/MINIMAX_CAPABILITY_VERIFICATION_INDEX.json            （脱敏后，可提交 Git）

不调用任何 MiniMax API，不写入密钥或完整资产内容。

用法：
  python scripts/rebuild_verification_index.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


# ── Status priority (higher = better) ─────────────────────────────────────────

_STATUS_PRIORITY = {
    "full_async_flow_verified": 7,
    "model_level_verified": 6,
    "capability_level_verified": 5,
    "success": 4,
    "success_with_warning": 3,
    "pending": 2,
    "failed": 1,
    "no_probe_record": 0,
}


def _better_status(existing: str | None, candidate: str) -> str:
    """Return the higher-priority status between existing and candidate."""
    if existing is None:
        return candidate
    return candidate if _STATUS_PRIORITY.get(candidate, -1) > _STATUS_PRIORITY.get(existing, -1) else existing


def _redact(value: str | None, max_len: int = 40) -> str | None:
    """Truncate long strings for safe storage in the index."""
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len] + "..."


def _safe_evidence(result: dict) -> dict:
    """Strip sensitive fields from a verification result."""
    safe = {}
    for key in (
        "capability_id", "status", "level", "http_status", "model",
        "protocol", "latency_ms", "output_type", "asset_saved",
        "file_id", "content_present", "content_length",
        "file_id_present", "file_size", "mime_type",
        "audio_chunk_count", "audio_bytes",
        "create_status", "task_id_present", "final_status",
        "poll_attempts", "download_success", "full_async_flow_verified",
    ):
        if key in result and result[key] is not None:
            val = result[key]
            if isinstance(val, str):
                val = _redact(val)
            safe[key] = val
    # Never store keys, tokens, full URLs, or file content
    for forbidden in ("api_key", "authorization", "token", "content", "audio",
                      "image_url", "image_urls", "audio_url", "file_path",
                      "asset_path", "path"):
        if forbidden in result:
            safe[forbidden] = "[REDACTED]"
    return safe


# ── Source readers ────────────────────────────────────────────────────────────

def _load_latest_json() -> dict[str, dict]:
    """Read from backend/runtime/capability_verification/latest.json."""
    vfile = BACKEND / "runtime" / "capability_verification" / "latest.json"
    if not vfile.exists():
        return {}
    try:
        data = json.loads(vfile.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for r in data.get("results", []):
        cid = r.get("capability_id")
        if not cid:
            continue
        status = r.get("status", "no_probe_record")
        best = _better_status(None, status)
        out[cid] = {
            "capability_id": cid,
            "best_status": best,
            "verified": best in ("full_async_flow_verified", "model_level_verified",
                                  "capability_level_verified", "success", "success_with_warning"),
            "last_success": r.get("ended_at") if status == "success" else None,
            "last_failure": r.get("ended_at") if status == "failed" else None,
            "source": "latest.json",
            "evidence": _safe_evidence(r),
        }
    return out


def _load_model_level_probe() -> dict[str, dict]:
    """Read from backend/runtime/reports/model_level_probe_report.json."""
    mfile = BACKEND / "runtime" / "reports" / "model_level_probe_report.json"
    if not mfile.exists():
        return {}
    try:
        data = json.loads(mfile.read_text(encoding="utf-8"))
    except Exception:
        return {}
    # Only keep the best result per capability (model_level is highest priority)
    out: dict[str, dict] = {}
    for r in data.get("results", []):
        cid = r.get("capability_id")
        ps = r.get("probe_status")
        if not cid or ps != "success":
            continue
        best = _better_status(out.get(cid, {}).get("best_status"), "model_level_verified")
        out[cid] = {
            "capability_id": cid,
            "best_status": best,
            "verified": True,
            "last_success": r.get("last_probed_at"),
            "last_failure": None,
            "source": "model_level_probe_report.json",
            "evidence": _safe_evidence(r),
        }
    return out


def _load_tts_ws_probe() -> dict[str, dict]:
    """Read from backend/runtime/reports/tts_ws_probe_report.json."""
    tfile = BACKEND / "runtime" / "reports" / "tts_ws_probe_report.json"
    if not tfile.exists():
        return {}
    try:
        data = json.loads(tfile.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if data.get("status") != "success":
        return {}
    return {
        "tts-ws": {
            "capability_id": "tts-ws",
            "best_status": "capability_level_verified",
            "verified": True,
            "last_success": data.get("probed_at"),
            "last_failure": None,
            "source": "tts_ws_probe_report.json",
            "evidence": {
                "capability_id": "tts-ws",
                "status": "success",
                "http_or_ws_status": data.get("http_or_ws_status"),
                "model": data.get("model"),
                "latency_ms": data.get("latency_ms"),
                "audio_chunk_count": data.get("audio_chunk_count"),
                "asset_saved": data.get("asset_saved"),
            },
        }
    }


def _load_verification_report_md() -> dict[str, dict]:
    """从 docs/MINIMAX_CAPABILITY_VERIFICATION_REPORT.md 读取 success 记录。

    解析 markdown 表格中 status=success 的能力。
    """
    report_file = BACKEND.parent / "docs" / "MINIMAX_CAPABILITY_VERIFICATION_REPORT.md"
    if not report_file.exists():
        return {}
    content = report_file.read_text(encoding="utf-8")

    out = {}
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if "能力 ID" in line or "---|---|" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            cap_id = parts[1].strip("` ")
            status = parts[2].strip()
            if cap_id and status == "success":
                out[cap_id] = {
                    "capability_id": cap_id,
                    "best_status": "success",
                    "verified": True,
                    "last_success": None,  # No timestamp in markdown table
                    "last_failure": None,
                    "source": "MINIMAX_CAPABILITY_VERIFICATION_REPORT.md",
                    "evidence": {"note": "success per Verification Report markdown"},
                }
    return out


def _load_matrix_doc() -> dict[str, dict]:
    """Read tts-async and lyrics-gen status from docs/MINIMAX_FULL_CAPABILITY_MATRIX.md."""
    doc = BACKEND.parent / "docs" / "MINIMAX_FULL_CAPABILITY_MATRIX.md"
    if not doc.exists():
        return {}
    content = doc.read_text(encoding="utf-8")
    out = {}

    # tts-async: full_async_flow_verified
    if re.search(r"`tts-async`.*?full_async_flow_verified", content) or \
       re.search(r"tts-async.*?全链路.*?成功", content):
        out["tts-async"] = {
            "capability_id": "tts-async",
            "best_status": "full_async_flow_verified",
            "verified": True,
            "last_success": None,  # No timestamp in matrix doc
            "last_failure": None,
            "source": "MINIMAX_FULL_CAPABILITY_MATRIX.md (section 5.9b)",
            "evidence": {"note": "full_async_flow verified per Matrix doc"},
        }

    # lyrics-gen: capability_level_verified
    if re.search(r"`lyrics-gen`.*?(?:medium.?验收完成|capability_level_verified|success)", content, re.DOTALL) or \
       re.search(r"lyrics-gen.*?验收完成", content):
        out["lyrics-gen"] = {
            "capability_id": "lyrics-gen",
            "best_status": "capability_level_verified",
            "verified": True,
            "last_success": None,
            "last_failure": None,
            "source": "MINIMAX_FULL_CAPABILITY_MATRIX.md (section 5.9b/6.2)",
            "evidence": {"note": "medium verification complete per Matrix doc"},
        }

    return out


# ── Index builder ────────────────────────────────────────────────────────────

def _build_index() -> dict:
    """Aggregate all sources with status priority."""
    # Load in priority order (higher-priority sources loaded later so they win)
    sources = [
        _load_matrix_doc(),        # lowest: doc assertions (tts-async, lyrics-gen fallback)
        _load_verification_report_md(),  # Verification Report markdown (safe successes)
        _load_latest_json(),       # file-upload/retrieve/content from latest run
        _load_model_level_probe(), # chat/tts-sync/image-t2i/music-gen
        _load_tts_ws_probe(),     # tts-ws
    ]

    merged: dict[str, dict] = {}
    for src in sources:
        for cid, record in src.items():
            if cid not in merged:
                merged[cid] = record
            else:
                # Status priority
                existing_status = merged[cid].get("best_status")
                new_status = record.get("best_status", "no_probe_record")
                better = _better_status(existing_status, new_status)
                merged[cid]["best_status"] = better
                merged[cid]["verified"] = better in (
                    "full_async_flow_verified", "model_level_verified",
                    "capability_level_verified", "success", "success_with_warning",
                )
                # Keep earliest success timestamp
                if record.get("last_success"):
                    if not merged[cid].get("last_success") or \
                       record["last_success"] < merged[cid]["last_success"]:
                        merged[cid]["last_success"] = record["last_success"]
                # Record failure if current best is poor
                if record.get("last_failure") and \
                   _STATUS_PRIORITY.get(better, 0) <= _STATUS_PRIORITY.get("failed", 0):
                    merged[cid]["last_failure"] = record["last_failure"]
                # Upgrade source if new is better
                if _STATUS_PRIORITY.get(new_status, -1) > _STATUS_PRIORITY.get(existing_status, -1):
                    merged[cid]["source"] = record.get("source", merged[cid].get("source"))

    return {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "rebuild_verification_index.py",
        "capabilities": merged,
    }


def _sanitise_for_docs(index: dict) -> dict:
    """Remove runtime-specific paths and truncate for the Git-safe snapshot."""
    out = dict(index)
    out["capabilities"] = {}
    for cid, rec in index.get("capabilities", {}).items():
        safe = dict(rec)
        evidence = dict(safe.get("evidence", {}))
        # Redact any runtime asset paths
        for key in list(evidence.keys()):
            if "path" in key.lower() and evidence[key] and "runtime" in str(evidence[key]).lower():
                evidence[key] = "[RUNTIME_PATH]"
        safe["evidence"] = evidence
        out["capabilities"][cid] = safe
    return out


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> dict:
    print("=" * 60)
    print("Rebuild Verification Index")
    print("=" * 60)

    index = _build_index()

    # Save runtime version (full, not committed to Git)
    runtime_path = BACKEND / "runtime" / "capability_verification" / "all_verified.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  runtime index -> {runtime_path.relative_to(BACKEND)}")

    # Save docs version (sanitised, committed to Git)
    docs_path = BACKEND.parent / "docs" / "MINIMAX_CAPABILITY_VERIFICATION_INDEX.json"
    docs_index = _sanitise_for_docs(index)
    docs_path.write_text(json.dumps(docs_index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  docs index    -> {docs_path.relative_to(BACKEND.parent)}")

    # Summary
    caps = index["capabilities"]
    verified = [cid for cid, rec in caps.items() if rec.get("verified")]
    print()
    print(f"  Total capabilities in index: {len(caps)}")
    print(f"  Verified: {len(verified)}")
    print(f"  Verified IDs: {sorted(verified)}")
    print()

    return index


if __name__ == "__main__":
    main()
