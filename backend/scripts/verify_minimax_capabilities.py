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

# CapabilityInvoker 支持的能力列表（全量 safe + medium + tts-ws）
_INVOKER_SUPPORTED = {
    "chat-openai", "chat-anthropic", "chat-responses-create",
    "chat-responses-tokens", "tts-sync", "tts-ws", "image-t2i",
    "lyrics-gen", "music-gen", "file-list", "voice-list",
    "models-openai-list", "models-anthropic-list",
    "models-openai-retrieve", "models-anthropic-retrieve",
}
RUNTIME_DIR = BACKEND / "runtime" / "capability_verification"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = BACKEND.parent / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


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
        "image-t2i",
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
        "tts-async",
    ],
}


# ── 单个能力验收 ─────────────────────────────────────────────────────────────

def _verify_single(
    cap_id: str,
    api_key: str,
    confirmations: dict | None = None,
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

    # CapabilityInvoker 支持的能力走统一路径
    if cap_id in _INVOKER_SUPPORTED:
        return _verify_via_invoker(cap_id, api_key, started_at, result, confirmations)

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
    "image-t2i":              {"model": "image-01", "prompt": "一只白色小猫坐在窗边，简洁插画风格", "aspect_ratio": "16:9", "n": 1},
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
    """通过 CapabilityInvoker 调用能力，主结果使用 VerificationResult 字段结构。"""
    payload = _INVOKER_PAYLOADS.get(cap_id, {})

    invoker = CapabilityInvoker(api_key=api_key, timeout=180.0)
    t0 = time.monotonic()

    try:
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
        is_medium = cap_id in ("tts-sync", "image-t2i", "lyrics-gen", "music-gen")

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
        if is_medium:
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
    parser.add_argument("--capability",
                        help="只验收指定能力（如 tts-ws），与 --level 配合可精确指定单个能力")
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
    }

    # 决定调用哪些能力
    if args.level == "safe":
        cap_ids = CAPABILITY_GROUPS["safe"]
    elif args.level == "medium":
        cap_ids = CAPABILITY_GROUPS["medium"]  # 仅 medium，不包含 safe
    else:
        cap_ids = CAPABILITY_GROUPS["safe"] + CAPABILITY_GROUPS["medium"] + CAPABILITY_GROUPS["high"]

    capabilities = _load_capabilities()
    models = _load_models()

    print("=" * 60)
    print(f"MiniMax 能力验收 - Level: {args.level}")
    print(f"API Key: {_redact(api_key)}")
    print(f"待验收能力数: {len(cap_ids)}")
    print("=" * 60)

    results: list[dict] = []
    for cap_id in cap_ids:
        cap_info = next((c for c in capabilities if c.get("id") == cap_id), None)
        cap_label = cap_info.get("label", cap_id) if cap_info else cap_id
        print(f"\n[{cap_id}] {cap_label}...", end=" ", flush=True)

        result = _verify_single(cap_id, api_key, confirmations)
        results.append(result)

        status_icon = {"success": "[OK]", "failed": "[FAIL]", "skipped": "-",
                       "unauthorized": "[WARN]", "quota_limited": "[WAIT]",
                       "success_with_warning": "[WARN2]"}.get(result["status"], "?")
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
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[OK] 保存 {out_path.relative_to(BACKEND)}")

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
