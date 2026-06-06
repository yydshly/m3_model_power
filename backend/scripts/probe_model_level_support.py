#!/usr/bin/env python3
"""
probe_model_level_support.py

对 MiniMax 模型执行低成本、模型级的逐项 probe 验证。

probe 范围（--scope low-cost 默认）：
  chat-openai   — 8 个 chat 模型逐项调用（直接 httpx，不走 CapabilityInvoker）
  chat-anthropic — 4 个 live Anthropic chat 模型逐项调用
  tts-sync      — 6 个 speech 模型逐项调用
  image-t2i     — 2 个 image 模型逐项调用
  music-gen     — music-2.6 单项调用

禁止执行（始终跳过）：
  video-t2v / video-i2v / video-s2v
  voice-clone-do / voice-design
  tts-async 长文本
  music-cover-prep

用法：
  python scripts/probe_model_level_support.py --scope low-cost    # 默认
  python scripts/probe_model_level_support.py --chat             # 只测 chat
  python scripts/probe_model_level_support.py --native-only --key-source api-key  # 最小 native 对照
  python scripts/probe_model_level_support.py --diagnose-auth    # 诊断鉴权配置
  python scripts/probe_model_level_support.py --dry-run          # 只打印，不执行

Key 选择：
  --key-source auto        # MINIMAX_TOKEN_PLAN_KEY > MINIMAX_API_KEY（默认）
  --key-source token-plan  # 只用 MINIMAX_TOKEN_PLAN_KEY
  --key-source api-key     # 只用 MINIMAX_API_KEY

输出：
  backend/runtime/reports/model_level_probe_report.json（不提交 Git）
  backend/runtime/reports/key_diagnosis.json（不提交 Git）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.minimax_core.clients.native import MiniMaxNativeClient

RUNTIME_REPORTS_DIR = BACKEND / "runtime" / "reports"
RUNTIME_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ── env loading ─────────────────────────────────────────────────────────────────

def _load_env() -> dict:
    env_path = BACKEND / ".env"
    if not env_path.exists():
        print("ERROR: backend/.env 不存在，请先配置", file=sys.stderr)
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


def _redact_key(key: str) -> str:
    """脱敏 Key，只显示前4后4位。"""
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def _key_fingerprint(key: str) -> dict:
    """计算 Key 指纹。"""
    if not key:
        return {"key_sha256_8": None, "key_prefix": None, "key_length": 0}
    h = hashlib.sha256(key.encode()).hexdigest()[:8]
    prefix = key[:4]
    return {
        "key_sha256_8": h,
        "key_prefix": prefix,
        "key_length": len(key),
    }


# ── key source resolution ─────────────────────────────────────────────────────────

class KeySourceError(Exception):
    """指定的 Key 类型不存在时抛出。"""
    pass


def resolve_key(key_source: str) -> tuple[str, str, dict]:
    """根据 key_source 策略解析 Key。

    Returns (key, key_source_name, fingerprint_dict)
    raises KeySourceError if required key is missing.
    """
    env = _load_env()
    token_plan_key = env.get("MINIMAX_TOKEN_PLAN_KEY", "")
    api_key = env.get("MINIMAX_API_KEY", "")

    if key_source == "token-plan":
        if not token_plan_key:
            raise KeySourceError("MINIMAX_TOKEN_PLAN_KEY is not set")
        fp = _key_fingerprint(token_plan_key)
        return token_plan_key, "MINIMAX_TOKEN_PLAN_KEY", fp

    if key_source == "api-key":
        if not api_key:
            raise KeySourceError("MINIMAX_API_KEY is not set")
        fp = _key_fingerprint(api_key)
        return api_key, "MINIMAX_API_KEY", fp

    # auto: prefer token_plan_key, fall back to api_key
    if token_plan_key:
        fp = _key_fingerprint(token_plan_key)
        return token_plan_key, "MINIMAX_TOKEN_PLAN_KEY", fp
    if api_key:
        fp = _key_fingerprint(api_key)
        return api_key, "MINIMAX_API_KEY", fp
    raise KeySourceError("Neither MINIMAX_TOKEN_PLAN_KEY nor MINIMAX_API_KEY is set")


# ── auth diagnosis ───────────────────────────────────────────────────────────────

def diagnose_auth(key_source: str = "auto") -> dict:
    """诊断 native API 鉴权配置，对比两个 Key 的指纹。

    诊断重点：
    1. key 来源 + 指纹（key_sha256_8）
    2. base_url / headers / endpoint 是否正确
    3. 两个 Key 的 sha256_8 是否相同（用于判断是否同一 Key）
    """
    env = _load_env()
    token_plan_key = env.get("MINIMAX_TOKEN_PLAN_KEY", "")
    api_key = env.get("MINIMAX_API_KEY", "")

    token_plan_fp = _key_fingerprint(token_plan_key)
    api_key_fp = _key_fingerprint(api_key)

    # Resolve the key that will actually be used
    try:
        actual_key, actual_source, actual_fp = resolve_key(key_source)
    except KeySourceError:
        actual_key = ""
        actual_source = "none"
        actual_fp = _key_fingerprint("")

    # Same key check
    same_key = (token_plan_fp["key_sha256_8"] == api_key_fp["key_sha256_8"]) if (token_plan_key and api_key) else None

    native_base_url = "https://api.minimaxi.com/v1"
    headers_present = {
        "authorization": bool(actual_key),
        "content_type": True,
    }

    return {
        "key_source_requested": key_source,
        "key_source_actual": actual_source,
        "key_preview": _redact_key(actual_key),
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
        "native_base_url": native_base_url,
        "tts_endpoint": "/t2a_v2",
        "image_endpoint": "/image_generation",
        "music_endpoint": "/music_generation",
        "headers_present": headers_present,
        "content_type": "application/json",
        "group_id_from_env": env.get("MINIMAX_GROUP_ID", "") or None,
        "env_file_path": str(BACKEND / ".env"),
        "dotenv_loaded": (BACKEND / ".env").exists(),
    }


def print_diagnose_auth_report(key_source: str = "auto") -> None:
    """诊断模式：打印鉴权信息并退出。"""
    d = diagnose_auth(key_source)
    print("=" * 60)
    print("Native API 鉴权诊断报告")
    print("=" * 60)
    print(f"  key_source_requested: {d['key_source_requested']}")
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
    print(f"  native_base_url:     {d['native_base_url']}")
    print(f"  tts_endpoint:        {d['tts_endpoint']}")
    print(f"  image_endpoint:      {d['image_endpoint']}")
    print(f"  music_endpoint:      {d['music_endpoint']}")
    print(f"  headers_present:     authorization={d['headers_present']['authorization']}, content_type={d['headers_present']['content_type']}")
    print(f"  group_id_from_env:  {d['group_id_from_env'] or '(未设置)'}")
    print(f"  dotenv_loaded:       {d['dotenv_loaded']}")
    print()
    print("说明：")
    print("  - key_sha256_8: Key 的前8位 SHA256 hash，用于比较两个脚本是否用同一 Key")
    print("  - same_key_label SAME_KEY: 两个 Key 的指纹相同（可能是同一 Key 复制到两个变量）")
    print("  - same_key_label DIFFERENT_KEYS: 两个 Key 都存在且指纹不同")
    print("  - same_key_label ONE_KEY_ONLY: 只有一个 Key 变量被设置")
    print("  - 1004 错误表示 Token/鉴权问题，非模型不可用")
    print("=" * 60)
    print()
    print(json.dumps(d, ensure_ascii=False, indent=2))

    # Also save to runtime
    diag_path = RUNTIME_REPORTS_DIR / "key_diagnosis.json"
    with diag_path.open("w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"\nJSON diagnosis -> {diag_path}")


# ── helpers ─────────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ── httpx helpers for chat ─────────────────────────────────────────────────────

OPENAI_BASE = "https://api.minimaxi.com/v1"
ANTHROPIC_BASE = "https://api.minimaxi.com/anthropic/v1"


def _chat_openai_via_httpx(
    api_key: str,
    model_id: str,
    group_id: str | None,
    timeout: float = 60.0,
) -> tuple[dict, float, int]:
    """直接用 httpx 调 OpenAI chat completions。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    params = {}
    if group_id:
        params["GroupId"] = group_id

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "只回复 OK"}],
        "max_tokens": 4,
        "temperature": 0,
    }
    url = f"{OPENAI_BASE}/chat/completions"
    start = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload, headers=headers, params=params)
        latency_ms = (time.perf_counter() - start) * 1000
        return resp.json(), latency_ms, resp.status_code


def _chat_anthropic_via_httpx(
    api_key: str,
    model_id: str,
    group_id: str | None,
    timeout: float = 60.0,
) -> tuple[dict, float, int]:
    """直接用 httpx 调 Anthropic messages。

    max_tokens=256，prompt 英文 "Reply exactly: OK"。
    """
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    params = {}
    if group_id:
        params["GroupId"] = group_id

    payload = {
        "model": model_id,
        "max_tokens": 256,
        "temperature": 0,
        "messages": [{"role": "user", "content": "Reply exactly: OK"}],
    }
    url = f"{ANTHROPIC_BASE}/messages"
    start = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload, headers=headers, params=params)
        latency_ms = (time.perf_counter() - start) * 1000
        return resp.json(), latency_ms, resp.status_code


# ── probe result builders ────────────────────────────────────────────────────────

def make_result(
    model_id: str,
    family: str,
    capability_id: str,
    protocol: str,
    scope: str,
    status: str,
    http_status: int | None = None,
    latency_ms: float | None = None,
    raw_http_success: bool | None = None,
    base_resp_success: bool | None = None,
    output_present: bool | None = None,
    parser_status: str | None = None,
    assertion_status: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    extra: dict | None = None,
) -> dict:
    return {
        "model_id": model_id,
        "family": family,
        "capability_id": capability_id,
        "protocol": protocol,
        "probe_scope": scope,
        "probe_status": status,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "raw_http_success": raw_http_success,
        "base_resp_success": base_resp_success,
        "output_present": output_present,
        "parser_status": parser_status,
        "assertion_status": assertion_status,
        "error_type": error_type,
        "error_message": error_message,
        "last_probed_at": ts(),
        "extra": extra or {},
    }


def _classify_status(
    http_status: int,
    base_resp_status: int | None,
    output_present: bool | None,
    parser_recognized: bool,
) -> tuple[str, str, str]:
    """根据 HTTP 和响应内容分类 probe 状态。"""
    raw_http_ok = 200 <= http_status < 300

    if not raw_http_ok:
        return "failed", "http_non_2xx", "none"

    if base_resp_status == 1004:
        return "auth_or_token_mismatch", "base_resp_1004", "auth_error"

    if base_resp_status is not None and base_resp_status != 0:
        return "failed", "base_resp_nonzero", "api_error"

    if output_present is True and parser_recognized:
        return "success", "parsed", "matched"

    if output_present is True and not parser_recognized:
        return "parser_mismatch", "unrecognized", "none"

    if output_present is False or output_present is None:
        return "http_success_but_output_missing", "no_output", "none"

    return "probe_assertion_failed", "structure_mismatch", "mismatch"


# ── model lists ────────────────────────────────────────────────────────────────

CHAT_OPENAI_MODELS = [
    "MiniMax-M3",
    "MiniMax-M2.7",
    "MiniMax-M2.7-highspeed",
    "MiniMax-M2.5",
    "MiniMax-M2.5-highspeed",
    "MiniMax-M2.1",
    "MiniMax-M2.1-highspeed",
    "MiniMax-M2",
]

ANTHROPIC_CHAT_MODELS = [
    "MiniMax-M3",
    "MiniMax-M2.7-highspeed",
    "MiniMax-M2.5-highspeed",
    "MiniMax-M2.1-highspeed",
]

SPEECH_MODELS = [
    "speech-2.8-hd",
    "speech-2.8-turbo",
    "speech-2.6-hd",
    "speech-2.6-turbo",
    "speech-02-hd",
    "speech-02-turbo",
]

IMAGE_MODELS = [
    "image-01",
    "image-01-live",
]

# Minimal native probe for key comparison
MINIMAL_NATIVE_MODELS = {
    "tts-sync": ["speech-02-turbo"],
    "image-t2i": ["image-01"],
    "music-gen": ["music-2.6"],
}


# ── Chat OpenAI probe ────────────────────────────────────────────────────────────

def probe_chat_openai(api_key: str, group_id: str | None, dry_run: bool = False) -> list[dict]:
    results = []
    for model_id in CHAT_OPENAI_MODELS:
        print(f"  [openai] {model_id} ...", end=" ", flush=True)
        if dry_run:
            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-openai",
                protocol="openai", scope="model_level", status="skipped",
                error_message="dry-run",
            ))
            print("skipped (dry-run)")
            continue

        try:
            raw, latency_ms, status_code = _chat_openai_via_httpx(api_key, model_id, group_id)
            text = ""
            if isinstance(raw, dict):
                text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            text_present = bool(text and text.strip())
            ok = status_code == 200 and text_present
            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-openai",
                protocol="openai", scope="model_level",
                status="success" if ok else "failed",
                http_status=status_code, latency_ms=round(latency_ms, 1),
                raw_http_success=(200 <= status_code < 300),
                base_resp_success=None,
                output_present=text_present,
                parser_status="parsed" if ok else "none",
                assertion_status="matched" if ok else "none",
                error_type=None if ok else "invoke_failed",
            ))
            print(f"{'OK' if ok else 'FAILED'} ({latency_ms:.0f}ms) text={text_present}")
        except Exception as exc:
            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-openai",
                protocol="openai", scope="model_level", status="failed",
                error_type=type(exc).__name__, error_message=str(exc),
            ))
            print(f"FAILED — {exc}")
    return results


def probe_chat_anthropic(api_key: str, group_id: str | None, dry_run: bool = False) -> list[dict]:
    """Anthropic probe：max_tokens=256，handle thinking block。"""
    results = []
    for model_id in ANTHROPIC_CHAT_MODELS:
        print(f"  [anthropic] {model_id} ...", end=" ", flush=True)
        if dry_run:
            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-anthropic",
                protocol="anthropic", scope="model_level", status="skipped",
                error_message="dry-run",
            ))
            print("skipped (dry-run)")
            continue

        try:
            raw, latency_ms, status_code = _chat_anthropic_via_httpx(api_key, model_id, group_id)

            text_content = ""
            thinking_present = False
            content_blocks = raw.get("content") if isinstance(raw, dict) else None

            if isinstance(content_blocks, list):
                for block in content_blocks:
                    if isinstance(block, dict):
                        btype = block.get("type")
                        if btype == "text":
                            text_content = block.get("text", "")
                        elif btype == "thinking":
                            thinking_present = True

            text_present = bool(text_content and text_content.strip())
            output_present = text_present or thinking_present

            if text_present:
                final_status = "success"
                parser_status = "parsed"
                assertion_status = "matched"
                error_type = None
            elif thinking_present:
                final_status = "probe_assertion_failed"
                parser_status = "thinking_only"
                assertion_status = "non_text_output"
                error_type = "thinking_block_only"
            else:
                final_status = "http_success_but_output_missing"
                parser_status = "no_content"
                assertion_status = "none"
                error_type = "no_text_or_thinking"

            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-anthropic",
                protocol="anthropic", scope="model_level",
                status=final_status,
                http_status=status_code, latency_ms=round(latency_ms, 1),
                raw_http_success=(200 <= status_code < 300),
                base_resp_success=None,
                output_present=output_present,
                parser_status=parser_status,
                assertion_status=assertion_status,
                error_type=error_type,
                extra={"thinking_present": thinking_present, "text_snippet": text_content[:20] if text_content else ""},
            ))
            status_label = "OK" if final_status == "success" else final_status
            print(f"{status_label} ({latency_ms:.0f}ms) text={text_present} thinking={thinking_present}")
        except Exception as exc:
            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-anthropic",
                protocol="anthropic", scope="model_level", status="failed",
                latency_ms=round(latency_ms, 1) if 'latency_ms' in dir() else None,
                error_type=type(exc).__name__, error_message=str(exc),
            ))
            print(f"FAILED — {exc}")
    return results


# ── Speech TTS probe ────────────────────────────────────────────────────────────

def probe_speech(native_client: MiniMaxNativeClient, model_ids: list[str] | None = None, dry_run: bool = False) -> list[dict]:
    """Speech TTS probe。model_ids=None 表示全部 6 个。"""
    results = []
    models = model_ids if model_ids is not None else SPEECH_MODELS
    for model_id in models:
        print(f"  [tts-sync] {model_id} ...", end=" ", flush=True)
        if dry_run:
            results.append(make_result(
                model_id=model_id, family="speech", capability_id="tts-sync",
                protocol="native", scope="model_level", status="skipped",
                error_message="dry-run",
            ))
            print("skipped (dry-run)")
            continue

        payload = {
            "model": model_id,
            "text": "OK",
            "voice_setting": {"voice_id": "female-tianmei", "speed": 1.0, "vol": 1.0, "pitch": 0},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
        }
        start = time.perf_counter()
        try:
            raw = native_client.tts_http(payload)
            latency_ms = (time.perf_counter() - start) * 1000

            base_resp = raw.get("base_resp") if isinstance(raw, dict) else None
            base_resp_status = base_resp.get("status_code") if isinstance(base_resp, dict) else None
            base_resp_success = (base_resp_status == 0)

            audio_hex = raw.get("data", {}).get("audio") if isinstance(raw, dict) else None
            extra_info = raw.get("extra_info") if isinstance(raw, dict) else {}
            audio_format = "mp3"
            audio_length = None
            audio_size = 0
            if isinstance(extra_info, dict):
                audio_format = extra_info.get("audio_format") or "mp3"
                audio_length = extra_info.get("audio_length")
                audio_size = extra_info.get("audio_size") or 0

            size_bytes = 0
            hex_decode_ok = False
            if audio_hex:
                try:
                    size_bytes = len(bytes.fromhex(audio_hex))
                    hex_decode_ok = size_bytes > 0
                except Exception:
                    size_bytes = 0

            output_present = bool(audio_hex)
            parser_recognized = hex_decode_ok and size_bytes > 0

            final_status, parser_status, assertion_status = _classify_status(
                http_status=200,
                base_resp_status=base_resp_status,
                output_present=output_present,
                parser_recognized=parser_recognized,
            )

            results.append(make_result(
                model_id=model_id, family="speech", capability_id="tts-sync",
                protocol="native", scope="model_level",
                status=final_status,
                http_status=200, latency_ms=round(latency_ms, 1),
                raw_http_success=True,
                base_resp_success=base_resp_success,
                output_present=output_present,
                parser_status=parser_status,
                assertion_status=assertion_status,
                extra={
                    "audio_format": audio_format,
                    "asset_size": size_bytes,
                    "audio_length": audio_length,
                    "audio_size": audio_size,
                    "hex_decode_ok": hex_decode_ok,
                    "base_resp_status": base_resp_status,
                },
            ))
            print(f"{final_status} ({latency_ms:.0f}ms) size={size_bytes}B fmt={audio_format}")
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(make_result(
                model_id=model_id, family="speech", capability_id="tts-sync",
                protocol="native", scope="model_level", status="failed",
                latency_ms=round(latency_ms, 1),
                raw_http_success=None,
                base_resp_success=None,
                output_present=False,
                parser_status="exception",
                error_type=type(exc).__name__, error_message=str(exc),
            ))
            print(f"FAILED ({latency_ms:.0f}ms) {exc}")
    return results


# ── Image probe ────────────────────────────────────────────────────────────────

def probe_image(native_client: MiniMaxNativeClient, model_ids: list[str] | None = None, dry_run: bool = False) -> list[dict]:
    """Image T2I probe。model_ids=None 表示全部 2 个。"""
    results = []
    models = model_ids if model_ids is not None else IMAGE_MODELS
    for model_id in models:
        print(f"  [image-t2i] {model_id} ...", end=" ", flush=True)
        if dry_run:
            results.append(make_result(
                model_id=model_id, family="image", capability_id="image-t2i",
                protocol="native", scope="model_level", status="skipped",
                error_message="dry-run",
            ))
            print("skipped (dry-run)")
            continue

        payload = {
            "model": model_id,
            "prompt": "simple red dot icon",
            "aspect_ratio": "1:1",
            "response_format": "url",
            "n": 1,
            "prompt_optimizer": False,
        }
        start = time.perf_counter()
        try:
            raw = native_client.image_generation(payload)
            latency_ms = (time.perf_counter() - start) * 1000

            base_resp = raw.get("base_resp") if isinstance(raw, dict) else None
            base_resp_status = base_resp.get("status_code") if isinstance(base_resp, dict) else None
            base_resp_success = (base_resp_status == 0)

            data_dict = raw.get("data") if isinstance(raw, dict) else None
            image_urls = data_dict.get("image_urls") if isinstance(data_dict, dict) else None
            image_urls = image_urls if isinstance(image_urls, list) else None

            metadata = raw.get("metadata") if isinstance(raw, dict) else {}
            metadata = metadata if isinstance(metadata, dict) else {}

            try:
                success_count = int(metadata.get("success_count", 0))
            except (ValueError, TypeError):
                success_count = 0
            try:
                failed_count = int(metadata.get("failed_count", 0))
            except (ValueError, TypeError):
                failed_count = 0

            url_count = len(image_urls) if image_urls else 0
            output_present = bool(image_urls and url_count >= 1)
            parser_recognized = output_present and success_count >= 1

            final_status, parser_status, assertion_status = _classify_status(
                http_status=200,
                base_resp_status=base_resp_status,
                output_present=output_present,
                parser_recognized=parser_recognized,
            )

            results.append(make_result(
                model_id=model_id, family="image", capability_id="image-t2i",
                protocol="native", scope="model_level",
                status=final_status,
                http_status=200, latency_ms=round(latency_ms, 1),
                raw_http_success=True,
                base_resp_success=base_resp_success,
                output_present=output_present,
                parser_status=parser_status,
                assertion_status=assertion_status,
                extra={
                    "image_urls_count": url_count,
                    "first_image_url_present": bool(image_urls and len(image_urls) > 0),
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "base_resp_status": base_resp_status,
                },
            ))
            print(f"{final_status} ({latency_ms:.0f}ms) urls={url_count} ok={success_count}")
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(make_result(
                model_id=model_id, family="image", capability_id="image-t2i",
                protocol="native", scope="model_level", status="failed",
                latency_ms=round(latency_ms, 1),
                raw_http_success=None,
                base_resp_success=None,
                output_present=False,
                parser_status="exception",
                error_type=type(exc).__name__, error_message=str(exc),
            ))
            print(f"FAILED ({latency_ms:.0f}ms) {exc}")
    return results


# ── Music probe ────────────────────────────────────────────────────────────────

def probe_music(native_client: MiniMaxNativeClient, model_ids: list[str] | None = None, dry_run: bool = False) -> list[dict]:
    """Music generation probe。model_ids=None 表示只测 music-2.6。"""
    results = []
    model_id = (model_ids or ["music-2.6"])[0]
    print(f"  [music-gen] {model_id} ...", end=" ", flush=True)
    if dry_run:
        results.append(make_result(
            model_id=model_id, family="music", capability_id="music-gen",
            protocol="native", scope="model_level", status="skipped",
            error_message="dry-run",
        ))
        print("skipped (dry-run)")
        return results

    payload = {
        "model": model_id,
        "prompt": "轻快民谣，简单吉他伴奏",
        "lyrics": "[Verse]\n晚风吹过窗台\n我把一天慢慢放下来\n",
        "stream": False,
        "output_format": "url",
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 256000,
            "format": "mp3",
        },
    }
    start = time.perf_counter()
    try:
        raw = native_client.music_generation(payload, timeout=180.0)
        latency_ms = (time.perf_counter() - start) * 1000

        base_resp = raw.get("base_resp") if isinstance(raw, dict) else None
        base_resp_status = base_resp.get("status_code") if isinstance(base_resp, dict) else None
        base_resp_success = (base_resp_status == 0)

        audio = raw.get("data", {}).get("audio") if isinstance(raw, dict) else None
        extra_info = raw.get("extra_info") if isinstance(raw, dict) else {}
        audio_format = "mp3"
        duration_ms = None
        if isinstance(extra_info, dict):
            audio_format = extra_info.get("audio_format") or "mp3"
            duration_ms = extra_info.get("music_duration")

        has_url = False
        has_hex = False
        size_bytes = 0
        if isinstance(audio, str):
            if audio.startswith("http"):
                has_url = True
            elif len(audio) > 100:
                has_hex = True
                try:
                    size_bytes = len(bytes.fromhex(audio))
                except Exception:
                    size_bytes = 0

        output_present = has_url or has_hex
        parser_recognized = output_present

        final_status, parser_status, assertion_status = _classify_status(
            http_status=200,
            base_resp_status=base_resp_status,
            output_present=output_present,
            parser_recognized=parser_recognized,
        )

        results.append(make_result(
            model_id=model_id, family="music", capability_id="music-gen",
            protocol="native", scope="model_level",
            status=final_status,
            http_status=200, latency_ms=round(latency_ms, 1),
            raw_http_success=True,
            base_resp_success=base_resp_success,
            output_present=output_present,
            parser_status=parser_status,
            assertion_status=assertion_status,
            extra={
                "audio_url_present": has_url,
                "audio_hex_present": has_hex,
                "audio_format": audio_format,
                "asset_size": size_bytes,
                "duration_ms": duration_ms,
                "base_resp_status": base_resp_status,
            },
        ))
        print(f"{final_status} ({latency_ms:.0f}ms) url={has_url} hex={has_hex}")
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        results.append(make_result(
            model_id=model_id, family="music", capability_id="music-gen",
            protocol="native", scope="model_level", status="failed",
            latency_ms=round(latency_ms, 1),
            raw_http_success=None,
            base_resp_success=None,
            output_present=False,
            parser_status="exception",
            error_type=type(exc).__name__, error_message=str(exc),
        ))
        print(f"FAILED ({latency_ms:.0f}ms) {exc}")
    return results


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MiniMax model-level probe script")
    parser.add_argument("--scope", default="low-cost",
                        help="Scope: low-cost (default), chat, speech, image, music, native-only, dry-run")
    parser.add_argument("--chat", action="store_true", help="Only probe chat models")
    parser.add_argument("--speech", action="store_true", help="Only probe speech models")
    parser.add_argument("--image", action="store_true", help="Only probe image models")
    parser.add_argument("--music", action="store_true", help="Only probe music models")
    parser.add_argument("--key-source", default="auto",
                        choices=["auto", "token-plan", "api-key"],
                        help="Key source: auto (default), token-plan, api-key")
    parser.add_argument("--diagnose-auth", action="store_true", help="Print auth diagnostics and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    # Diagnose mode - print and exit
    if args.diagnose_auth:
        print_diagnose_auth_report(args.key_source)
        return

    dry_run = args.dry_run or args.scope == "dry-run"

    print(f"[probe_model_level_support] scope={args.scope} key-source={args.key_source} dry={dry_run}")
    print()

    if not dry_run:
        # Resolve key based on key-source
        try:
            api_key, key_source_name, key_fp = resolve_key(args.key_source)
        except KeySourceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"Using key: source={key_source_name} preview={_redact_key(api_key)} sha256_8={key_fp['key_sha256_8']}")
        print()

        # OpenAI/Anthropic chat 允许传 group_id
        env = _load_env()
        group_id = env.get("MINIMAX_GROUP_ID") or None
        # Native API 不传 group_id（与 verify 对齐）
        native_client = MiniMaxNativeClient(
            api_key=api_key,
            timeout=120.0,
            group_id=None,
        )
    else:
        api_key = ""
        group_id = None
        native_client = None  # type: ignore[assignment]
        key_source_name = "dry-run"

    all_results: list[dict] = []

    scope_chat = args.chat or args.scope in ("low-cost", "chat")
    scope_speech = args.speech or args.scope in ("low-cost", "speech", "native-only")
    scope_image = args.image or args.scope in ("low-cost", "image", "native-only")
    scope_music = args.music or args.scope in ("low-cost", "music", "native-only")
    scope_native_only = args.scope == "native-only"

    if scope_chat:
        print("[chat-openai]")
        all_results.extend(probe_chat_openai(api_key, group_id, dry_run))
        print()
        print("[chat-anthropic]")
        all_results.extend(probe_chat_anthropic(api_key, group_id, dry_run))
        print()

    if scope_speech:
        model_ids = MINIMAL_NATIVE_MODELS["tts-sync"] if scope_native_only else None
        print(f"[tts-sync]{' (minimal)' if scope_native_only else ''}")
        all_results.extend(probe_speech(native_client, model_ids, dry_run))
        print()

    if scope_image:
        model_ids = MINIMAL_NATIVE_MODELS["image-t2i"] if scope_native_only else None
        print(f"[image-t2i]{' (minimal)' if scope_native_only else ''}")
        all_results.extend(probe_image(native_client, model_ids, dry_run))
        print()

    if scope_music:
        model_ids = MINIMAL_NATIVE_MODELS["music-gen"] if scope_native_only else None
        print(f"[music-gen]{' (minimal)' if scope_native_only else ''}")
        all_results.extend(probe_music(native_client, model_ids, dry_run))
        print()

    success = sum(1 for r in all_results if r["probe_status"] == "success")
    failed = sum(1 for r in all_results if r["probe_status"] == "failed")
    skipped = sum(1 for r in all_results if r["probe_status"] == "skipped")
    probe_assertion_failed = sum(1 for r in all_results if r["probe_status"] == "probe_assertion_failed")
    parser_mismatch = sum(1 for r in all_results if r["probe_status"] == "parser_mismatch")
    http_success_but_missing = sum(1 for r in all_results if r["probe_status"] == "http_success_but_output_missing")
    auth_or_token_mismatch = sum(1 for r in all_results if r["probe_status"] == "auth_or_token_mismatch")

    print(f"Results: {success} success, {failed} failed, {skipped} skipped, "
          f"{probe_assertion_failed} probe_assertion_failed, {parser_mismatch} parser_mismatch, "
          f"{http_success_but_missing} http_success_but_output_missing, "
          f"{auth_or_token_mismatch} auth_or_token_mismatch ({len(all_results)} total)")

    if not dry_run:
        report = {
            "generated_at": ts(),
            "scope": args.scope,
            "key_source": key_source_name,
            "key_sha256_8": key_fp["key_sha256_8"],
            "summary": {
                "total": len(all_results),
                "success": success,
                "failed": failed,
                "skipped": skipped,
                "probe_assertion_failed": probe_assertion_failed,
                "parser_mismatch": parser_mismatch,
                "http_success_but_output_missing": http_success_but_missing,
                "auth_or_token_mismatch": auth_or_token_mismatch,
            },
            "results": all_results,
        }
        json_path = RUNTIME_REPORTS_DIR / "model_level_probe_report.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"JSON report -> {json_path}")

        # Show non-success details
        non_success = [r for r in all_results if r["probe_status"] != "success"]
        if non_success:
            print("\nNon-success probes:")
            for r in non_success:
                extra = r.get("extra", {})
                print(f"  {r['model_id']} ({r['capability_id']}): status={r['probe_status']} "
                      f"http={r['http_status']} base_resp={extra.get('base_resp_status','?')} "
                      f"output={r['output_present']} parser={r.get('parser_status','?')} "
                      f"assertion={r.get('assertion_status','?')} "
                      f"{r['error_type'] or ''} {r['error_message'] or ''}")


if __name__ == "__main__":
    main()
