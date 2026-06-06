#!/usr/bin/env python3
"""
MiniMax 能力验收脚本 —— verify_minimax_capabilities.py

验收范围分级：

  Level 1（安全，默认执行）：
    models-openai-list, models-anthropic-list,
    models-openai-retrieve, models-anthropic-retrieve,
    chat-openai (max_tokens=16),
    chat-anthropic (max_tokens=16),
    chat-responses-create (短 input),
    chat-responses-tokens (短 input),
    file-list, voice-list

  Level 2（中等成本，默认不执行，需 --confirm-cost）：
    tts-sync, image-t2i, lyrics-gen, music-gen

  Level 3（高成本/可能计费，默认禁止，需 --confirm-high-cost）：
    voice-clone-do, voice-design,
    video-t2v, video-i2v, video-s2v,
    music-cover-prep, tts-async 长文本

用法：
  python scripts/verify_minimax_capabilities.py --level safe        # 默认
  python scripts/verify_minimax_capabilities.py --level medium --confirm-cost
  python scripts/verify_minimax_capabilities.py --level high --confirm-cost --confirm-high-cost

输出：
  backend/runtime/capability_verification/latest.json
  docs/MINIMAX_CAPABILITY_VERIFICATION_REPORT.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

BACKEND = Path(__file__).resolve().parent.parent

# ── Core 客户端（minimax_core）─────────────────────────────────────────────────
from app.minimax_core.clients.openai import MiniMaxOpenAIClient
from app.minimax_core.clients.anthropic import MiniMaxAnthropicClient
from app.minimax_core.clients.native import MiniMaxNativeClient
from app.minimax_core.clients.files import MiniMaxFilesClient
from app.minimax_core.contracts import AssetRef, UnifiedErrorException, VerificationResult
from app.minimax_core.invoker import CapabilityInvoker, NotImplementedCapability
from app.config import settings

# CapabilityInvoker 支持的能力列表（全量 safe + medium + tts-ws）
_INVOKER_SUPPORTED = {
    "chat-openai", "chat-anthropic", "chat-responses-create",
    "chat-responses-tokens", "tts-sync", "tts-ws", "tts-async", "image-t2i",
    "image-i2i",
    "lyrics-gen", "music-gen", "file-list", "voice-list",
    "models-openai-list", "models-anthropic-list",
    "models-openai-retrieve", "models-anthropic-retrieve",
}
RUNTIME_DIR = BACKEND / "runtime" / "capability_verification"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = BACKEND.parent / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Status priority for aggregate index (higher = better)
_STATUS_PRIORITY = {
    "full_async_flow_verified": 7,
    "model_level_verified": 6,
    "capability_level_verified": 5,
    "success": 4,
    "success_with_warning": 3,
    "integration_ready_but_probe_pending_valid_image_url": 2,
    "pending": 2,
    "failed": 1,
    "no_probe_record": 0,
    "skipped": 0,
    "unauthorized": 0,
    "quota_limited": 0,
    "risk_gate_blocked": 0,
}


def _better_status(existing: str | None, candidate: str) -> str:
    if existing is None:
        return candidate
    return candidate if _STATUS_PRIORITY.get(candidate, -1) > _STATUS_PRIORITY.get(existing, -1) else existing


def _safe_evidence(result: dict) -> dict:
    """Strip sensitive fields from a verification result for storage in index."""
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
            safe[key] = result[key]
    for forbidden in ("api_key", "authorization", "token", "content",
                      "image_url", "image_urls", "audio_url", "path"):
        if forbidden in result:
            safe[forbidden] = "[REDACTED]"
    return safe


def _update_aggregate_index(new_results: list[dict]) -> None:
    """Update the aggregate verification index with new results.

    Strategy:
    - Load existing aggregate index (if any)
    - For each new result:
        - If new status is better than existing, upgrade the record
        - If new result is a failure and existing is a success, add last_failure
          but DO NOT overwrite the successful best_status
    - Save both runtime/all_verified.json and docs/MINIMAX_CAPABILITY_VERIFICATION_INDEX.json
    """
    runtime_index_path = RUNTIME_DIR / "all_verified.json"
    docs_index_path = DOCS_DIR / "MINIMAX_CAPABILITY_VERIFICATION_INDEX.json"

    # Load existing aggregate
    aggregate: dict[str, dict] = {}
    if runtime_index_path.exists():
        try:
            aggregate = json.loads(runtime_index_path.read_text(encoding="utf-8"))
            aggregate = aggregate.get("capabilities", {})
        except Exception:
            aggregate = {}

    # Merge new results
    for r in new_results:
        cid = r.get("capability_id")
        if not cid:
            continue
        status = r.get("status", "no_probe_record")
        is_success = status in ("success", "success_with_warning", "full_async_flow_verified",
                                 "model_level_verified", "capability_level_verified")

        existing = aggregate.get(cid, {})
        existing_status = existing.get("best_status")

        # Determine new best status
        if is_success:
            new_best = _better_status(existing_status, status)
        else:
            # Failures don't overwrite successes; they just add last_failure
            if existing_status and _STATUS_PRIORITY.get(existing_status, 0) >= _STATUS_PRIORITY.get("success", 0):
                new_best = existing_status  # keep existing success
            else:
                new_best = status

        record = {
            "capability_id": cid,
            "best_status": new_best,
            "verified": new_best in ("full_async_flow_verified", "model_level_verified",
                                      "capability_level_verified", "success", "success_with_warning"),
            "last_success": r.get("ended_at") if is_success else existing.get("last_success"),
            "last_failure": r.get("ended_at") if not is_success else existing.get("last_failure"),
            "source": "verify_minimax_capabilities.py",
            "evidence": _safe_evidence(r),
        }
        aggregate[cid] = record

    # Build full index document
    index_doc = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "verify_minimax_capabilities.py",
        "capabilities": aggregate,
    }

    # Write runtime version (full)
    runtime_index_path.write_text(json.dumps(index_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write docs version (sanitised, committed)
    def _sanitise(idx: dict) -> dict:
        out = dict(idx)
        out["capabilities"] = {}
        for c_id, rec in idx.get("capabilities", {}).items():
            safe = dict(rec)
            evidence = {k: ("[RUNTIME_PATH]" if "path" in k.lower() and "runtime" in str(v).lower() else v)
                        for k, v in safe.get("evidence", {}).items()}
            safe["evidence"] = evidence
            out["capabilities"][c_id] = safe
        return out

    docs_index_path.write_text(json.dumps(_sanitise(index_doc), ensure_ascii=False, indent=2), encoding="utf-8")


def _redact(key: str) -> str:
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def _key_fingerprint(key: str) -> dict:
    """计算 Key 指纹（用于比较两个脚本是否用同一 Key）。"""
    if not key:
        return {"key_sha256_8": None, "key_prefix": None, "key_length": 0}
    h = hashlib.sha256(key.encode()).hexdigest()[:8]
    return {"key_sha256_8": h, "key_prefix": key[:4], "key_length": len(key)}


def diagnose_auth() -> dict:
    """诊断 verify 脚本使用的 Key 配置（Token Plan Only 模式）。"""
    env = _load_env()
    token_plan_key = env.get("MINIMAX_TOKEN_PLAN_KEY", "")
    api_key = env.get("MINIMAX_API_KEY", "")

    token_plan_fp = _key_fingerprint(token_plan_key)
    api_key_fp = _key_fingerprint(api_key)
    same_key = (token_plan_fp["key_sha256_8"] == api_key_fp["key_sha256_8"]) if (token_plan_key and api_key) else None

    # verify 脚本默认使用 MINIMAX_TOKEN_PLAN_KEY
    actual_key = token_plan_key
    actual_fp = token_plan_fp
    key_source_actual = "MINIMAX_TOKEN_PLAN_KEY"

    return {
        "key_source_actual": key_source_actual,
        "key_preview": _redact(actual_key),
        "key_sha256_8": actual_fp["key_sha256_8"],
        "key_prefix": actual_fp["key_prefix"],
        "key_length": actual_fp["key_length"],
        "token_empty": not bool(actual_key),
        "has_token_plan_key": bool(token_plan_key),
        "has_api_key": bool(api_key),
        "token_plan_key_sha256_8": token_plan_fp["key_sha256_8"],
        "api_key_sha256_8": api_key_fp["key_sha256_8"],
        "same_key": same_key,
        "same_key_label": "SAME_KEY" if same_key else ("DIFFERENT_KEYS" if (token_plan_key and api_key) else "ONE_KEY_ONLY"),
        "base_url": "https://api.minimaxi.com",
        "native_base_url": "https://api.minimaxi.com/v1",
        "env_file_path": str(BACKEND / ".env"),
        "dotenv_loaded": (BACKEND / ".env").exists(),
    }


def print_diagnose_auth_report() -> None:
    """诊断模式：打印鉴权信息并退出。"""
    d = diagnose_auth()
    print("=" * 60)
    print("verify_minimax_capabilities.py 鉴权诊断报告")
    print("=" * 60)
    print(f"  key_source_actual:   {d['key_source_actual']}")
    print(f"  key_preview:         {d['key_preview']}")
    print(f"  key_sha256_8:       {d['key_sha256_8']}")
    print(f"  key_prefix:          {d['key_prefix']}")
    print(f"  key_length:          {d['key_length']}")
    print(f"  token_empty:         {d['token_empty']}")
    print(f"  same_key:           {d['same_key']} ({d['same_key_label']})")
    print(f"  has_token_plan_key: {d['has_token_plan_key']}")
    print(f"  has_api_key:        {d['has_api_key']}")
    print(f"  token_plan_key_sha256_8: {d['token_plan_key_sha256_8']}")
    print(f"  api_key_sha256_8:        {d['api_key_sha256_8']}")
    print(f"  base_url:            {d['base_url']}")
    print(f"  native_base_url:     {d['native_base_url']}")
    print(f"  dotenv_loaded:       {d['dotenv_loaded']}")
    print()
    print("说明：")
    print("  - verify 脚本默认只使用 MINIMAX_TOKEN_PLAN_KEY（Token Plan Only 模式）")
    print("  - MINIMAX_API_KEY 仅用于可选诊断，不参与默认验收")
    print("  - key_sha256_8 用于比较两个脚本是否用同一 Key")
    print("=" * 60)
    print()
    print(json.dumps(d, ensure_ascii=False, indent=2))

    diag_path = RUNTIME_DIR / "verify_key_diagnosis.json"
    with diag_path.open("w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"\nJSON diagnosis -> {diag_path}")


def _load_env() -> dict:
    env_path = BACKEND / ".env"
    if not env_path.exists():
        print("ERROR: backend/.env 不存在", file=sys.stderr)
        sys.exit(1)
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _load_capabilities() -> list[dict]:
    with (BACKEND / "config" / "capabilities.yaml").open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc.get("capabilities", [])


def _load_models() -> list[dict]:
    with (BACKEND / "config" / "models.yaml").open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc.get("models", [])


# ── 能力分级定义 ─────────────────────────────────────────────────────────────

CAPABILITY_GROUPS = {
    "safe": [
        "models-openai-list",
        "models-anthropic-list",
        "models-openai-retrieve",
        "models-anthropic-retrieve",
        "chat-openai",
        "chat-anthropic",
        "chat-responses-create",
        "chat-responses-tokens",
        "file-list",
        "voice-list",
    ],
    "medium": [
        "tts-sync",
        "tts-ws",
        "tts-async",
        "image-t2i",
        "image-i2i",
        "lyrics-gen",
        "music-gen",
    ],
    "high": [
        "voice-clone-do",
        "voice-design",
        "video-t2v",
        "video-i2v",
        "video-s2v",
        "music-cover-prep",
    ],
}


# ── 单个能力验收 ─────────────────────────────────────────────────────────────

def _verify_single(
    cap_id: str,
    api_key: str,
    confirmations: dict | None = None,
    file_id: str | None = None,
    reference_image: str | None = None,
    image_url: str | None = None,
) -> dict:
    """使用 CapabilityInvoker 验收单个能力。"""
    confirmations = confirmations or {}
    started_at = datetime.now(timezone.utc).isoformat()
    result: dict = {
        "capability_id": cap_id,
        "status": "skipped",
        "level": "safe",
        "http_status": None,
        "model": None,
        "protocol": None,
        "started_at": started_at,
        "ended_at": None,
        "latency_ms": None,
        "error_code": None,
        "error_message": None,
        "response_shape_ok": None,
        "sensitive_data_redacted": True,
        # medium specific
        "output_type": None,
        "asset_saved": False,
        "asset_committed": False,
    }

    # multipart 上传走独立路径
    if cap_id == "file-upload":
        return _verify_via_multipart(cap_id, api_key, started_at, result, confirmations)

    # image-i2i 需要先上传参考图
    if cap_id == "image-i2i":
        return _verify_via_invoker_with_ref_image(cap_id, api_key, started_at, result, confirmations, reference_image, image_url)

    # CapabilityInvoker 支持的能力走统一路径
    if cap_id in _INVOKER_SUPPORTED:
        return _verify_via_invoker(cap_id, api_key, started_at, result, confirmations)

    # file-retrieve / file-content 走 files client
    if cap_id in ("file-retrieve", "file-content"):
        return _verify_via_files(cap_id, api_key, started_at, result, file_id)

    # 其余能力（models-* / high / video 等）走旧 client 路径
    return _verify_via_client(cap_id, api_key, started_at, result)


# ── CapabilityInvoker 路径 ─────────────────────────────────────────────────

# payload 映射
_INVOKER_PAYLOADS: dict[str, dict] = {
    "chat-openai":            {"model": "MiniMax-M3", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16},
    "chat-anthropic":         {"model": "MiniMax-M3", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16},
    "chat-responses-create":  {"model": "MiniMax-M3", "input": "Hi"},
    "chat-responses-tokens":  {"model": "MiniMax-M3", "input": "Hi"},
    "tts-sync":               {"model": "speech-02-turbo", "text": "你好，这是 MiniMax 语音能力验收。", "voice_setting": {"voice_id": "female-tianmei"}, "audio_setting": {"sample_rate": 32000, "format": "mp3"}},
    "tts-ws":                 {"model": "speech-02-turbo", "text": "OK", "voice_id": "female-tianmei", "speed": 1.0, "sample_rate": 32000, "audio_format": "mp3"},
    "tts-async":             {"model": "speech-02-turbo", "text": "你好，这是异步语音合成测试。", "voice_setting": {"voice_id": "female-tianmei"}, "audio_setting": {"sample_rate": 32000, "format": "mp3"}},
    "image-t2i":              {"model": "image-01", "prompt": "一只白色小猫坐在窗边，简洁插画风格", "aspect_ratio": "16:9", "n": 1},
    "image-i2i":             {"model": "image-01", "prompt": "将图片转换为插画风格", "img_url": "https://example.com/sample.jpg", "n": 1},
    "lyrics-gen":             {"mode": "write_full_song", "prompt": "一首关于夏天傍晚的轻快民谣"},
    "music-gen":              {"model": "music-2.6", "prompt": "轻快民谣，简单吉他伴奏", "lyrics": "[Verse]\n晚风吹过窗台\n我把一天慢慢放下来\n[Chorus]\n月光落在肩上\n心也变得安静起来", "stream": False, "output_format": "url", "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"}},
    "file-list":              {},
    "voice-list":             {"voice_type": "all"},
    "models-openai-list":     {},
    "models-anthropic-list":  {},
    "models-openai-retrieve": {"model": "MiniMax-M3"},
    "models-anthropic-retrieve": {"model": "MiniMax-M3"},
}


def _verify_via_invoker(cap_id: str, api_key: str, started_at: str, result: dict, confirmations: dict) -> dict:
    """通过 CapabilityInvoker 调用能力，主结果使用 VerificationResult 字段结构。

    async 能力（tts-ws）：使用 asyncio.run(invoke_async()) 将 asyncio.run() 放在 CLI 入口层，
    而不是 core invoker 内部。
    """
    payload = _INVOKER_PAYLOADS.get(cap_id, {})

    invoker = CapabilityInvoker(api_key=api_key, timeout=180.0)
    t0 = time.monotonic()

    # tts-ws 和 tts-async 是原生 async 能力，在 CLI 层使用 asyncio.run() 调用 invoke_async()
    _is_async_capability = (cap_id in {"tts-ws", "tts-async"})

    try:
        if _is_async_capability:
            import asyncio as _asyncio
            response = _asyncio.run(invoker.invoke_async(cap_id, payload, confirmations=confirmations))
        else:
            response = invoker.invoke(cap_id, payload, confirmations=confirmations)
        latency_ms = int((time.monotonic() - t0) * 1000)
        ended_at = datetime.now(timezone.utc).isoformat()

        # 防御：即使 CapabilityInvoker 返回 ok=False 的响应（而非抛出异常），
        # 也不应判定为 success。
        if not response.ok:
            # 构造一个与抛出的 UnifiedErrorException 等价的结构
            raise UnifiedErrorException(
                ok=False,
                capability_id=cap_id,
                error_type=getattr(response, "error_type", None) or "unknown",
                error_code=getattr(response, "error_code", None),
                message=getattr(response, "message", None) or f"{cap_id} returned ok=False",
                http_status=getattr(response, "http_status", None) or 200,
                retryable=False,
                redacted=True,
            )

        # medium 能力特有字段（从 response.assets 统一填充）
        is_medium = cap_id in ("tts-sync", "tts-ws", "tts-async", "image-t2i", "lyrics-gen", "music-gen")

        result.update({
            "latency_ms": latency_ms,
            "ended_at": ended_at,
            "status": "success",
            "response_shape_ok": True,
            "model": response.model,
            "output_type": response.output_type,
            "level": "medium" if is_medium else "safe",
            "http_status": 200,
            # assets 统一来自 response.assets
            "assets": [a.model_dump() for a in response.assets] if response.assets else [],
        })

        # medium 能力特有字段（_handle_medium_result 保留以处理 asset_saved / asset_committed）
        # tts-async 有专用处理器，不走 _handle_medium_result（会误覆盖 full flow 字段）
        if is_medium and cap_id != "tts-async":
            _handle_medium_result(cap_id, response.raw, result)

        # tts-async 专用 full-flow 字段提取
        if cap_id == "tts-async":
            _handle_tts_async_result(response.raw, result)

    except NotImplementedCapability as exc:
        result.update({
            "status": "skipped",
            "error_message": f"not_implemented: {exc.capability_id}",
            "ended_at": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        ended_at = datetime.now(timezone.utc).isoformat()
        err_msg = str(exc)
        http_status = None
        error_type = "unknown"
        if hasattr(exc, "http_status") and exc.http_status:
            http_status = exc.http_status
        if hasattr(exc, "message"):
            err_msg = exc.message
        if hasattr(exc, "error_type") and exc.error_type:
            error_type = exc.error_type
        result.update({
            "latency_ms": latency_ms,
            "ended_at": ended_at,
            "status": "failed",
            "http_status": http_status,
            "error_type": error_type,
            "error_message": err_msg,
            "response_shape_ok": False,
        })

    return result


def _verify_via_invoker_with_ref_image(
    cap_id: str,
    api_key: str,
    started_at: str,
    result: dict,
    confirmations: dict,
    reference_image_path: str | None,
    image_url: str | None = None,
) -> dict:
    """Upload reference image (if local path given) then call image-i2i via CapabilityInvoker.

    Supports two modes:
    - Local file path: upload to MiniMax, use returned file_id
    - URL-based payload: use img_url with public URL (no upload needed)
    """
    # RiskGate: image-i2i requires confirm_asset_source
    cap_op = next((c for c in _load_capabilities() if c.get("id") == cap_id), None)
    if cap_op and not confirmations.get("confirm_asset_source"):
        result.update({
            "status": "risk_gate_blocked",
            "error_message": "image-i2i requires confirm_asset_source=true",
            "ended_at": datetime.now(timezone.utc).isoformat(),
        })
        return result

    # Build base payload from _INVOKER_PAYLOADS
    payload = dict(_INVOKER_PAYLOADS.get(cap_id, {}))

    # If a local reference image path is given, upload it and swap in file_id
    if reference_image_path:
        upload_result = _upload_reference_image(reference_image_path, api_key)
        if "error" in upload_result:
            result.update({
                "status": "failed",
                "error_message": f"reference image upload failed: {upload_result['error']}",
                "latency_ms": upload_result.get("latency_ms"),
                "ended_at": datetime.now(timezone.utc).isoformat(),
            })
            return result

        file_id = upload_result.get("file_id")
        result["reference_file_id"] = file_id
        result["reference_image_upload_ms"] = upload_result.get("latency_ms")
        # Replace URL-based reference with uploaded file_id
        payload["input_file_id"] = file_id
        # Remove URL-based fields
        for key in ("subject_reference", "img_url"):
            if key in payload:
                del payload[key]
    elif image_url:
        # Use the provided public image URL directly — no upload needed
        payload["img_url"] = image_url
        result["reference_image_public_url"] = image_url
    elif "subject_reference" not in payload and "input_file_id" not in payload and "img_url" not in payload:
        # Neither local file nor URL payload — skip
        result.update({
            "status": "skipped",
            "error_message": "image-i2i requires --reference-image <path> or --image-url <url>",
            "ended_at": datetime.now(timezone.utc).isoformat(),
        })
        return result

    # 3. Call via CapabilityInvoker (same as _verify_via_invoker)
    invoker = CapabilityInvoker(api_key=api_key, timeout=180.0)
    t0 = time.monotonic()

    try:
        response = invoker.invoke(cap_id, payload, confirmations=confirmations)
        latency_ms = int((time.monotonic() - t0) * 1000)
        ended_at = datetime.now(timezone.utc).isoformat()

        if not response.ok:
            raise UnifiedErrorException(
                ok=False,
                capability_id=cap_id,
                error_type=getattr(response, "error_type", None) or "unknown",
                error_code=getattr(response, "error_code", None),
                message=getattr(response, "message", None) or f"{cap_id} returned ok=False",
                http_status=getattr(response, "http_status", None) or 200,
                retryable=False,
                redacted=True,
            )

        result.update({
            "latency_ms": latency_ms,
            "ended_at": ended_at,
            "status": "success",
            "response_shape_ok": True,
            "model": response.model,
            "output_type": response.output_type,
            "level": "medium",
            "http_status": 200,
            "assets": [a.model_dump() for a in response.assets] if response.assets else [],
        })
        _handle_medium_result(cap_id, response.raw, result)

    except NotImplementedCapability as exc:
        result.update({
            "status": "skipped",
            "error_message": f"not_implemented: {exc.capability_id}",
            "ended_at": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        ended_at = datetime.now(timezone.utc).isoformat()
        err_msg = str(exc)
        http_status = None
        error_type = "unknown"
        if hasattr(exc, "http_status") and exc.http_status:
            http_status = exc.http_status
        if hasattr(exc, "message"):
            err_msg = exc.message
        if hasattr(exc, "error_type") and exc.error_type:
            error_type = exc.error_type
        result.update({
            "latency_ms": latency_ms,
            "ended_at": ended_at,
            "status": "failed",
            "http_status": http_status,
            "error_type": error_type,
            "error_message": err_msg,
            "response_shape_ok": False,
        })

    return result


# ── 旧 client 路径（high / video / voice-clone 等 Invoker 未覆盖的能力）──────

_cap_client_config: dict[str, tuple[str, str, dict | None, float]] = {
    "voice-clone-do":        ("native",   "voice_clone",           {"file_id": "dummy", "voice_id": "test_script_voice", "need_noise_reduction": False},  30),
    "voice-design":          ("native",   "voice_design",          {"prompt": "a calm female voice", "preview_text": "hello"},  30),
    "video-t2v":             ("native",   "video_generation",      {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "duration": 5},  180),
    "video-i2v":             ("native",   "video_generation",      {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "first_frame_image": "https://example.com/f.jpg", "duration": 5},  180),
    "video-s2v":             ("native",   "video_generation",      {"model": "MiniMax-Hailuo-02", "prompt": "a cat", "subject_reference": [{"type": "character", "image": ["https://example.com/s.jpg"]}]},  180),
    "music-cover-prep":       ("native",   "music_generation",     {"purpose": "song"},  180),
    "tts-async":             ("native",   "tts_http",             {"model": "speech-02-turbo", "text": "测试语音", "voice_setting": {"voice_id": "female-shaonu"}},  180),
}


def _verify_via_client(cap_id: str, api_key: str, started_at: str, result: dict) -> dict:
    """对 CapabilityInvoker 未覆盖的能力（models-* / video / voice-clone）走 client 直接调用。"""
    if cap_id not in _cap_client_config:
        result["status"] = "skipped"
        result["error_message"] = "no config for this capability"
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        return result

    client_type, method_name, body, timeout = _cap_client_config[cap_id]

    try:
        clients = {
            "openai":    MiniMaxOpenAIClient(api_key=api_key, timeout=timeout),
            "anthropic": MiniMaxAnthropicClient(api_key=api_key, timeout=timeout),
            "native":    MiniMaxNativeClient(api_key=api_key, timeout=timeout),
            "files":     MiniMaxFilesClient(api_key=api_key, timeout=timeout),
        }
        client = clients[client_type]
    except Exception as exc:
        result["status"] = "failed"
        result["error_message"] = f"client_init_error: {exc}"
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        return result

    t0 = time.monotonic()
    status_code: int | None = None
    data: dict | None = None
    err: str | None = None

    try:
        method = getattr(client, method_name)
        data = method(body) if body else method()
        status_code = 200
    except Exception as exc:
        err = str(exc)
        if hasattr(exc, "http_status"):
            status_code = exc.http_status
            err = exc.message if hasattr(exc, "message") else str(exc)

    latency_ms = int((time.monotonic() - t0) * 1000)
    result["latency_ms"] = latency_ms
    result["ended_at"] = datetime.now(timezone.utc).isoformat()
    result["http_status"] = status_code

    if err:
        result["status"] = "failed"
        result["error_message"] = err
        return result

    if status_code in (401, 403):
        result["status"] = "unauthorized"
        result["error_message"] = f"HTTP {status_code}"
        return result
    if status_code == 429:
        result["status"] = "quota_limited"
        result["error_message"] = "HTTP 429 Rate Limited"
        return result
    if status_code and status_code >= 400:
        result["status"] = "failed"
        result["error_message"] = f"HTTP {status_code}: {str(data)[:200]}"
        return result

    shape_ok = _check_response_shape(cap_id, data)
    result["response_shape_ok"] = shape_ok
    result["status"] = "success" if shape_ok else "success_with_warning"
    result["model"] = body.get("model") if body else None

    if cap_id in ("tts-sync", "image-t2i", "lyrics-gen", "music-gen"):
        result["level"] = "medium"
        _handle_medium_result(cap_id, data, result)

    return result


# ── multipart 上传路径 ─────────────────────────────────────────────────────────

_MULTIPART_TEST_CONTENT = b"MiniMax Token Plan file capability probe.\nThis is a safe test file.\n"


def _upload_reference_image(image_path: str, api_key: str) -> dict:
    """Upload a local image file to MiniMax and return the file_id.

    Returns {"file_id": ..., "http_status": ..., "latency_ms": ...} on success,
    or {"error": ...} on failure.
    """
    from pathlib import Path
    p = Path(image_path)
    if not p.exists():
        return {"error": f"reference image not found: {image_path}"}

    env = _load_env()
    group_id = env.get("MINIMAX_GROUP_ID", "")
    url = f"{settings.minimax_base_url}/v1/files/upload"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {}
    if group_id:
        params["GroupId"] = group_id

    t0 = time.monotonic()
    try:
        with open(p, "rb") as f:
            image_bytes = f.read()
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        files = {"file": (p.name, image_bytes, mime)}
        data = {"purpose": "retrieval"}
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, params=params, files=files, data=data)
        latency_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code >= 400:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}", "latency_ms": latency_ms}

        json_data = resp.json()
        base_resp = json_data.get("base_resp", {})
        if base_resp.get("status_code") not in (None, 0, "0"):
            return {"error": f"base_resp.status_code={base_resp.get('status_code')}: {base_resp.get('status_msg', '')}", "latency_ms": latency_ms}

        file_item = json_data.get("file", json_data)
        return {
            "file_id": file_item.get("file_id"),
            "http_status": resp.status_code,
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        return {"error": str(exc)[:200]}


def _verify_via_multipart(cap_id: str, api_key: str, started_at: str, result: dict, confirmations: dict) -> dict:
    """通过 httpx multipart 上传验收 file-upload。"""
    # RiskGate: file-upload 需要 confirm_asset_source
    cap_op = next((c for c in _load_capabilities() if c.get("id") == cap_id), None)
    if cap_op and not confirmations.get("confirm_asset_source"):
        result.update({
            "status": "risk_gate_blocked",
            "error_message": "file-upload requires confirm_asset_source=true",
            "ended_at": datetime.now(timezone.utc).isoformat(),
        })
        return result

    # 从 capability example 中获取 purpose（file-upload 为 "retrieval"）
    example_purpose = None
    if cap_op and cap_op.get("example"):
        example_purpose = cap_op["example"].get("purpose")

    env = _load_env()
    group_id = env.get("MINIMAX_GROUP_ID", "")
    url = f"{settings.minimax_base_url}/v1/files/upload"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {}
    if group_id:
        params["GroupId"] = group_id

    t0 = time.monotonic()
    try:
        files = {"file": ("probe_file.txt", _MULTIPART_TEST_CONTENT, "text/plain")}
        data: dict = {}
        if example_purpose:
            data["purpose"] = example_purpose
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, params=params, files=files, data=data)
        latency_ms = int((time.monotonic() - t0) * 1000)
        result["latency_ms"] = latency_ms
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        result["http_status"] = resp.status_code

        if resp.status_code >= 400:
            result["status"] = "failed"
            try:
                err_json = resp.json()
                result["error_message"] = err_json.get("base_resp", {}).get("status_msg") or err_json.get("message") or resp.text[:200]
            except ValueError:
                result["error_message"] = resp.text[:200]
            return result

        json_data = resp.json()
        base_resp = json_data.get("base_resp", {})
        if base_resp.get("status_code") not in (None, 0, "0"):
            result["status"] = "failed"
            result["error_message"] = f"base_resp.status_code={base_resp.get('status_code')}: {base_resp.get('status_msg', '')}"
            return result

        # file-upload API returns {"file": {...}, "base_resp": {...}}
        file_item = json_data.get("file", json_data)
        result["status"] = "success"
        result["response_shape_ok"] = True
        result["file_id_present"] = bool(file_item.get("file_id"))
        result["file_id"] = file_item.get("file_id")
        result["file_size"] = file_item.get("bytes") or len(_MULTIPART_TEST_CONTENT)
        result["mime_type"] = file_item.get("mime_type") or "text/plain"
        return result

    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        result.update({
            "latency_ms": latency_ms,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "error_message": str(exc)[:200],
        })
        return result


def _verify_via_files(cap_id: str, api_key: str, started_at: str, result: dict, file_id: str | None) -> dict:
    """通过 MiniMaxFilesClient 验收 file-retrieve / file-content。"""
    if not file_id:
        result.update({
            "status": "skipped",
            "error_message": "file_id not provided (use --file-id)",
            "ended_at": datetime.now(timezone.utc).isoformat(),
        })
        return result

    files_client = MiniMaxFilesClient(api_key=api_key, timeout=30)
    t0 = time.monotonic()
    try:
        if cap_id == "file-retrieve":
            data = files_client.retrieve_file(file_id)
        elif cap_id == "file-content":
            content_bytes, ctype = files_client.retrieve_content(file_id)
            data = {"content_length": len(content_bytes), "content_type": ctype}
        else:
            data = None
        latency_ms = int((time.monotonic() - t0) * 1000)
        result["latency_ms"] = latency_ms
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        result["http_status"] = 200
        result["status"] = "success"
        result["response_shape_ok"] = True
        result["file_id"] = file_id
        if cap_id == "file-retrieve":
            result["filename"] = data.get("filename") or data.get("name")
            result["bytes"] = data.get("bytes")
            result["purpose"] = data.get("purpose")
        elif cap_id == "file-content":
            result["content_present"] = True
            result["content_length"] = data.get("content_length")
        return result
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        err_msg = str(exc)
        http_status = getattr(exc, "http_status", None)
        result.update({
            "latency_ms": latency_ms,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "http_status": http_status,
            "status": "failed",
            "error_message": err_msg[:200],
        })
        return result


def _handle_tts_async_result(data: dict | None, result: dict) -> None:
    """处理 tts-async full flow 验证结果。

    data 来自 UnifiedResponse.raw，包含 create/poll/download 各环节的闭环状态。
    """
    if not data:
        return

    result["create_status"] = "success" if data.get("create_ok") else "failed"
    result["task_id_present"] = bool(data.get("task_id"))
    result["task_id"] = data.get("task_id")
    result["task_token_present"] = bool(data.get("task_token_present"))
    result["initial_file_id_present"] = bool(data.get("initial_file_id"))

    # usage_characters 从 create_raw 根级别提取（API 将其放在根级而非 extra_info）
    create_raw = data.get("create_raw") or {}
    result["usage_characters"] = create_raw.get("usage_characters")

    result["query_status"] = None  # query 隐含在 final_status 中
    result["final_status"] = data.get("final_status")
    result["final_file_id_present"] = bool(data.get("final_file_id"))
    result["poll_attempts"] = data.get("poll_attempts")
    result["download_attempted"] = data.get("download_attempted")
    result["download_success"] = data.get("download_success")
    result["audio_bytes"] = data.get("audio_bytes")
    result["full_async_flow_verified"] = data.get("full_async_flow_verified")

    # asset_saved 从 assets 列表推断
    assets = result.get("assets") or []
    if assets and isinstance(assets, list):
        first_asset = assets[0]
        result["asset_saved"] = bool(first_asset.get("path"))
        result["asset_path"] = first_asset.get("path")
        result["asset_size"] = first_asset.get("size_bytes")
    else:
        result["asset_saved"] = False
        result["asset_path"] = None
        result["asset_size"] = None

    result["asset_committed"] = False


def _handle_medium_result(cap_id: str, data: dict | None, result: dict) -> None:
    """处理 medium 能力结果，构建 AssetRef 并填充 result。

    语义规则：
      - asset_saved:  音频/图片文件是否实际写入 runtime/assets/
      - asset_reference_saved: URL/引用是否记录（未下载文件）
      - committed:     永远为 False（runtime 资产不提交 Git）

    result 中统一新增 assets[] 字段（list[AssetRef]）。
    """
    runtime_dir = Path(__file__).resolve().parent.parent / "runtime" / "assets"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    result["assets"] = []

    if cap_id == "tts-sync":
        result["output_type"] = "audio"
        if not (data and isinstance(data, dict)):
            return

        extra = data.get("extra_info") or {}
        audio_format = (extra.get("audio_format") if isinstance(extra, dict) else None) or "mp3"
        data_dict = data.get("data") if isinstance(data.get("data"), dict) else None
        audio_hex = data_dict.get("audio") if data_dict else None

        if audio_hex:
            audio_bytes = bytes.fromhex(audio_hex)
            size_bytes = len(audio_bytes)
            out_path = runtime_dir / f"tts_sync_sample.{audio_format}"
            try:
                out_path.write_bytes(audio_bytes)
                asset_saved = True
            except Exception as e:
                result["asset_save_error"] = str(e)
                asset_saved = False

            ref = AssetRef(
                type="audio",
                format=audio_format,
                path=str(out_path.relative_to(runtime_dir.parent.parent)) if asset_saved else None,
                url=None,
                size_bytes=size_bytes if asset_saved else None,
                duration_ms=extra.get("audio_length") if isinstance(extra, dict) else None,
                committed=False,
            )
            result["assets"] = [ref.model_dump()]
            result["audio_returned"] = True
            result["audio_payload_type"] = "hex"
            result["audio_format"] = audio_format
            result["audio_length"] = extra.get("audio_length") if isinstance(extra, dict) else None
            result["audio_sample_rate"] = extra.get("audio_sample_rate") if isinstance(extra, dict) else None
            result["usage_characters"] = extra.get("usage_characters") if isinstance(extra, dict) else None
            result["asset_saved"] = asset_saved
            result["asset_committed"] = False
            result["asset_size"] = size_bytes if asset_saved else None
        else:
            result["audio_returned"] = False
            result["audio_payload_type"] = "unknown"
            result["audio_format"] = audio_format

    elif cap_id == "image-t2i":
        result["output_type"] = "image"
        if not (data and isinstance(data, dict)):
            return

        img_data = data.get("data") if isinstance(data.get("data"), dict) else None
        image_urls = img_data.get("image_urls") if img_data else None
        metadata = data.get("metadata") or {}
        success_count = int(metadata.get("success_count", 0)) if metadata.get("success_count") else 0
        failed_count = int(metadata.get("failed_count", 0)) if metadata.get("failed_count") else 0

        result["image_urls_count"] = len(image_urls) if image_urls else 0
        result["first_image_url_present"] = bool(image_urls and len(image_urls) > 0)
        result["success_count"] = success_count
        result["failed_count"] = failed_count
        result["task_id"] = data.get("id") or data.get("trace_id")

        if image_urls and len(image_urls) > 0:
            first_url = image_urls[0]
            ref = AssetRef(
                type="image",
                format=None,
                path=None,
                url=first_url,
                size_bytes=None,
                committed=False,
            )
            result["assets"] = [ref.model_dump()]
            result["audio_returned"] = True
            result["audio_payload_type"] = "url"
            result["asset_saved"] = False
            result["asset_reference_saved"] = True
            result["asset_committed"] = False
        else:
            result["audio_returned"] = False
            result["audio_payload_type"] = "unknown"
            result["asset_saved"] = False
            result["asset_reference_saved"] = False

    elif cap_id == "lyrics-gen":
        result["output_type"] = "text"
        if not (data and isinstance(data, dict)):
            return

        lyrics = data.get("lyrics") or ""
        result["song_title"] = data.get("song_title") or ""
        result["style_tags"] = data.get("style_tags") or ""
        result["lyrics_preview"] = lyrics[:200] if lyrics else ""
        result["audio_returned"] = bool(lyrics)
        result["audio_payload_type"] = "text"
        # 歌词是纯文本，不走 AssetRef（AssetRef 面向二进制/URL 资产）
        result["asset_saved"] = False
        result["asset_reference_saved"] = bool(lyrics)
        result["asset_committed"] = False

    elif cap_id == "music-gen":
        result["output_type"] = "music"
        if not (data and isinstance(data, dict)):
            return

        extra = data.get("extra_info") or {}
        audio_format = (extra.get("audio_format") if isinstance(extra, dict) else None) or "mp3"
        img_data = data.get("data") if isinstance(data.get("data"), dict) else None
        audio_url = img_data.get("audio_url") or img_data.get("music_url") if img_data else None
        audio_raw = img_data.get("audio") if img_data else None
        # audio_raw 可以是 URL 字符串（output_format=url）或 hex 字符串（output_format=hex）
        audio_is_url = isinstance(audio_raw, str) and audio_raw.startswith("http")
        if audio_is_url and not audio_url:
            audio_url = audio_raw
            audio_raw = None

        result["audio_returned"] = bool(audio_url or audio_raw)
        result["audio_payload_type"] = "url" if audio_url else ("hex" if audio_raw else "unknown")
        result["audio_url_present"] = bool(audio_url)
        result["audio_hex_present"] = bool(audio_raw and not audio_is_url)
        result["audio_format"] = audio_format
        result["music_duration"] = extra.get("music_duration") if isinstance(extra, dict) else None
        result["music_sample_rate"] = extra.get("music_sample_rate") if isinstance(extra, dict) else None
        result["bitrate"] = extra.get("bitrate") if isinstance(extra, dict) else None

        if audio_url:
            ref = AssetRef(
                type="audio",
                format=audio_format,
                path=None,
                url=audio_url,
                size_bytes=None,
                duration_ms=extra.get("music_duration") if isinstance(extra, dict) else None,
                committed=False,
            )
            result["assets"] = [ref.model_dump()]
            result["asset_saved"] = False
            result["asset_reference_saved"] = True
            result["asset_committed"] = False
        elif audio_raw and not audio_is_url:
            audio_bytes = bytes.fromhex(audio_raw)
            size_bytes = len(audio_bytes)
            out_path = runtime_dir / f"music_gen_sample.{audio_format}"
            try:
                out_path.write_bytes(audio_bytes)
                asset_saved = True
            except Exception as e:
                result["asset_save_error"] = str(e)
                asset_saved = False
                size_bytes = None

            ref = AssetRef(
                type="audio",
                format=audio_format,
                path=str(out_path.relative_to(runtime_dir.parent.parent)) if asset_saved else None,
                url=None,
                size_bytes=size_bytes,
                duration_ms=extra.get("music_duration") if isinstance(extra, dict) else None,
                committed=False,
            )
            result["assets"] = [ref.model_dump()]
            result["asset_saved"] = asset_saved
            result["asset_reference_saved"] = False
            result["asset_committed"] = False
            result["asset_size"] = size_bytes
        else:
            result["asset_saved"] = False
            result["asset_reference_saved"] = False

    elif cap_id == "tts-async":
        result["output_type"] = "audio"
        if not (data and isinstance(data, dict)):
            return

        result["create_status"] = "success" if data.get("create_ok") else "failed"
        result["task_id_present"] = bool(data.get("task_id"))
        result["task_id"] = data.get("task_id")
        result["task_token_present"] = bool(data.get("task_token_present"))
        result["initial_file_id_present"] = bool(data.get("initial_file_id"))
        result["usage_characters"] = data.get("create_raw", {}).get("extra_info", {}).get("usage_characters") if isinstance(data.get("create_raw"), dict) else None
        result["query_status"] = None  # query is implicit in final_status
        result["final_status"] = data.get("final_status")
        result["final_file_id_present"] = bool(data.get("final_file_id"))
        result["poll_attempts"] = data.get("poll_attempts")
        result["download_attempted"] = data.get("download_attempted")
        result["download_success"] = data.get("download_success")
        result["audio_bytes"] = data.get("audio_bytes")
        result["full_async_flow_verified"] = data.get("full_async_flow_verified")

        # Determine asset_saved based on assets list if available
        if result.get("assets") and len(result.get("assets", [])) > 0:
            first_asset = result["assets"][0]
            result["asset_saved"] = bool(first_asset.get("path"))
            result["asset_path"] = first_asset.get("path")
        else:
            result["asset_saved"] = False
            result["asset_path"] = None

        result["asset_committed"] = False



def _check_response_shape(cap_id: str, data) -> bool:
    if data is None:
        return False
    if cap_id == "models-openai-list":
        return isinstance(data, dict) and "data" in data
    if cap_id == "models-anthropic-list":
        # MiniMax Anthropic 端点返回 OpenAI 兼容格式 {data: [...]} 而非标准 Anthropic {models: [...]}
        return isinstance(data, dict) and "data" in data
    if cap_id == "models-openai-retrieve":
        return isinstance(data, dict) and "id" in data
    if cap_id == "models-anthropic-retrieve":
        # MiniMax Anthropic 端点返回 OpenAI 兼容格式 {id: ...} 而非标准 Anthropic {name: ...}
        return isinstance(data, dict) and "id" in data
    if cap_id in ("chat-openai", "chat-anthropic", "chat-responses-create"):
        return isinstance(data, dict)
    if cap_id == "file-list":
        return isinstance(data, dict)
    if cap_id == "voice-list":
        return isinstance(data, dict)
    if cap_id in ("tts-sync", "image-t2i", "music-gen", "lyrics-gen", "tts-async"):
        return isinstance(data, dict)
    if cap_id in ("voice-clone-do", "voice-design", "video-t2v", "video-i2v", "video-s2v", "music-cover-prep"):
        return isinstance(data, dict)
    return True


# ── 报告生成 ─────────────────────────────────────────────────────────────────

def _generate_markdown(results: list[dict]) -> str:
    lines = [
        "# MiniMax 能力验收报告",
        "",
        f"> 生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        "## 验收摘要",
        "",
        f"| 状态 | 数量 |",
        f"|---|---|",
    ]
    from collections import Counter
    counts = Counter(r["status"] for r in results)
    for status, cnt in sorted(counts.items()):
        lines.append(f"| {status} | {cnt} |")
    lines.append("")

    lines += [
        "## 详细结果",
        "",
        "| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: x["capability_id"]):
        lines.append(
            f"| {r['capability_id']} | {r['status']} "
            f"| {r.get('http_status', '-')} | {r.get('latency_ms', '-')} "
            f"| {r.get('model', '-')} | {r.get('error_message', '-')[:60] if r.get('error_message') else '-'} |"
        )
    lines += ["", "---", "*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*"]
    return "\n".join(lines)


# ── 主入口 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MiniMax 能力验收脚本")
    parser.add_argument("--level", choices=["safe", "medium", "high"], default="safe",
                        help="验收级别：safe(默认)/medium/high")
    parser.add_argument("--confirm-cost", action="store_true",
                        help="确认中等成本验收（tts-sync, image-t2i 等）")
    parser.add_argument("--confirm-high-cost", action="store_true",
                        help="确认高成本验收（video, voice-clone 等）")
    parser.add_argument("--confirm-paid", action="store_true",
                        help="确认付费能力（may_charge_extra=true）")
    parser.add_argument("--confirm-destructive", action="store_true",
                        help="确认破坏性操作（is_destructive=true）")
    parser.add_argument("--confirm-asset-source", action="store_true",
                        help="确认素材来源能力（requires_uploaded_asset=true）")
    parser.add_argument("--confirm-long-running", action="store_true",
                        help="确认长任务能力（is_long_running=true）")
    parser.add_argument("--confirm-existing-task", action="store_true",
                        help="确认已有任务能力（requires_existing_task=true）")
    parser.add_argument("--confirm-quota", action="store_true",
                        help="确认配额超额能力（tts-async 字符数超阈值）")
    parser.add_argument("--diagnose-auth", action="store_true",
                        help="打印 Key 诊断信息并退出")
    parser.add_argument("--poll", nargs="?", const="true", default="true",
                        help="tts-async 是否轮询（默认 true，可用 --poll false 关闭）")
    parser.add_argument("--download", nargs="?", const="true", default="true",
                        help="tts-async 是否下载（默认 true，可用 --download false 关闭）")
    parser.add_argument("--max-poll-attempts", type=int, default=30,
                        help="tts-async 最大轮询次数（默认 30）")
    parser.add_argument("--poll-interval", type=float, default=2.0,
                        help="tts-async 轮询间隔秒数（默认 2.0）")
    parser.add_argument("--capability",
                        help="只验收指定能力（如 tts-ws），与 --level 配合可精确指定单个能力")
    parser.add_argument("--file-id",
                        help="指定 file_id（用于 file-retrieve / file-content 验收）")
    parser.add_argument("--reference-image",
                        help="指定参考图路径（用于 image-i2i 验收）")
    parser.add_argument("--image-url",
                        help="指定公开图片 URL（用于 image-i2i 验收，覆盖 payload 默认 img_url）")
    args = parser.parse_args()

    # Diagnose mode
    if args.diagnose_auth:
        print_diagnose_auth_report()
        return

    if args.level == "medium" and not args.confirm_cost:
        print("ERROR: medium 级别需要 --confirm-cost 参数确认费用风险。", file=sys.stderr)
        sys.exit(1)
    if args.level == "high" and not (args.confirm_cost and args.confirm_high_cost):
        print("ERROR: high 级别需要 --confirm-cost --confirm-high-cost 双重确认。", file=sys.stderr)
        sys.exit(1)

    # safe / medium / high 分级安全隔离
    # --level safe      → 只跑 safe（默认）
    # --level medium    → 只跑 medium（需 --confirm-cost）
    # --level high      → 跑 medium + high（需双重确认）
    # --level safe+medium → 只在本任务中用于 isolated medium 模式（不通过 arg 暴露）

    # --capability 精确指定：跳过 level 分组，只跑单个能力（需 --confirm-cost 如果是 medium）
    if args.capability:
        cap_ids = [args.capability]
        if args.level == "medium" and not args.confirm_cost:
            print(f"ERROR: --capability {args.capability} 属于 medium 级别，需要 --confirm-cost。", file=sys.stderr)
            sys.exit(1)
    elif args.level == "safe":
        cap_ids = CAPABILITY_GROUPS["safe"]
    elif args.level == "medium":
        cap_ids = CAPABILITY_GROUPS["medium"]  # 仅 medium，不包含 safe
    else:
        cap_ids = CAPABILITY_GROUPS["safe"] + CAPABILITY_GROUPS["medium"] + CAPABILITY_GROUPS["high"]

    env = _load_env()
    token_plan_key = env.get("MINIMAX_TOKEN_PLAN_KEY", "")

    if not token_plan_key:
        print("ERROR: MINIMAX_TOKEN_PLAN_KEY 未配置（Token Plan Only 模式）", file=sys.stderr)
        print("提示：backend/.env 中配置 MINIMAX_TOKEN_PLAN_KEY", file=sys.stderr)
        sys.exit(1)
    api_key = token_plan_key

    # 构建 RiskGate 确认字典
    confirmations = {
        "confirm_paid": bool(args.confirm_paid),
        "confirm_high_cost": bool(args.confirm_high_cost),
        "confirm_destructive": bool(args.confirm_destructive),
        "confirm_asset_source": bool(args.confirm_asset_source),
        "confirm_long_running": bool(args.confirm_long_running),
        "confirm_existing_task": bool(args.confirm_existing_task),
        "confirm_quota": bool(args.confirm_quota),
        "poll": args.poll == "true",
        "download": args.download == "true",
        "max_poll_attempts": int(args.max_poll_attempts),
        "poll_interval": float(args.poll_interval),
    }

    capabilities = _load_capabilities()
    models = _load_models()

    print("=" * 60)
    print(f"MiniMax 能力验收 - Level: {args.level}")
    print(f"API Key: {_redact(api_key)}")
    print(f"待验收能力数: {len(cap_ids)}")
    print("=" * 60)

    # 链式 file_id：file-upload 成功后会将 file_id 存入此变量，供给后续 file-retrieve/file-content 使用
    chained_file_id: str | None = args.file_id

    results: list[dict] = []
    for cap_id in cap_ids:
        cap_info = next((c for c in capabilities if c.get("id") == cap_id), None)
        cap_label = cap_info.get("label", cap_id) if cap_info else cap_id
        print(f"\n[{cap_id}] {cap_label}...", end=" ", flush=True)

        result = _verify_single(cap_id, api_key, confirmations, file_id=chained_file_id, reference_image=args.reference_image, image_url=args.image_url)
        results.append(result)

        # 如果是 file-upload 成功，提取 file_id 供后续 file-retrieve/file-content 使用
        if cap_id == "file-upload" and result["status"] == "success" and result.get("file_id"):
            chained_file_id = result["file_id"]
            print(f"  (chained file_id: {chained_file_id})", end=" ")

        status_icon = {"success": "[OK]", "failed": "[FAIL]", "skipped": "-",
                       "unauthorized": "[WARN]", "quota_limited": "[WAIT]",
                       "success_with_warning": "[WARN2]",
                       "risk_gate_blocked": "[GATED]"}.get(result["status"], "?")
        print(f"{status_icon} {result['status']} ({result.get('latency_ms', '-')}ms)")

        if result.get("error_message"):
            print(f"    错误：{result['error_message'][:100]}")

    # 保存结果
    api_key_fp = _key_fingerprint(api_key)
    output: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "level": args.level,
        "api_key_tail": _redact(api_key),
        "api_key_sha256_8": api_key_fp["key_sha256_8"],
        "total": len(results),
        "results": results,
    }

    out_path = RUNTIME_DIR / "latest.json"
    # Merge mode: combine this run with existing latest.json (preserve cross-run history)
    existing: dict = {}
    if out_path.exists():
        try:
            with open(out_path, encoding="utf-8") as ef:
                existing = json.load(ef)
        except Exception:
            existing = {}
    merged = {r["capability_id"]: r for r in results}
    for prev in existing.get("results", []):
        pid = prev.get("capability_id")
        if pid not in merged:
            merged[pid] = prev
    output["results"] = list(merged.values())
    output["total"] = len(output["results"])
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Update aggregate verification index (non-destructive merge)
    _update_aggregate_index(results)
    print("\r\n[OK] save " + str(out_path.relative_to(BACKEND)))





    md = _generate_markdown(results)
    md_path = DOCS_DIR / "MINIMAX_CAPABILITY_VERIFICATION_REPORT.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[OK] 保存 {md_path.relative_to(BACKEND.parent)}")

    # 摘要
    from collections import Counter
    counts = Counter(r["status"] for r in results)
    print("\n" + "═" * 60)
    print("验收摘要")
    print("═" * 60)
    for status, cnt in sorted(counts.items()):
        print(f"  {status}: {cnt}")
    print("═" * 60)


if __name__ == "__main__":
    main()
