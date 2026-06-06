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
  python scripts/probe_model_level_support.py --speech           # 只测 speech
  python scripts/probe_model_level_support.py --image            # 只测 image
  python scripts/probe_model_level_support.py --music            # 只测 music
  python scripts/probe_model_level_support.py --dry-run         # 只打印，不执行

输出：
  backend/runtime/reports/model_level_probe_report.json（不提交 Git）
"""
from __future__ import annotations

import argparse
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
    """直接用 httpx 调 Anthropic messages。"""
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
        "max_tokens": 4,
        "messages": [{"role": "user", "content": "只回复 OK"}],
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
    output_present: bool | None = None,
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
        "output_present": output_present,
        "error_type": error_type,
        "error_message": error_message,
        "last_probed_at": ts(),
        "extra": extra or {},
    }


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
                output_present=text_present,
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
            text = ""
            if isinstance(raw, dict):
                content = raw.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            break
                elif isinstance(content, str):
                    text = content
            text_present = bool(text and text.strip())
            ok = status_code == 200 and text_present
            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-anthropic",
                protocol="anthropic", scope="model_level",
                status="success" if ok else "failed",
                http_status=status_code, latency_ms=round(latency_ms, 1),
                output_present=text_present,
                error_type=None if ok else "invoke_failed",
            ))
            print(f"{'OK' if ok else 'FAILED'} ({latency_ms:.0f}ms) text={text_present}")
        except Exception as exc:
            results.append(make_result(
                model_id=model_id, family="chat", capability_id="chat-anthropic",
                protocol="anthropic", scope="model_level", status="failed",
                error_type=type(exc).__name__, error_message=str(exc),
            ))
            print(f"FAILED — {exc}")
    return results


# ── Speech TTS probe ────────────────────────────────────────────────────────────

def probe_speech(native_client: MiniMaxNativeClient, dry_run: bool = False) -> list[dict]:
    results = []
    for model_id in SPEECH_MODELS:
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
            data_dict = raw.get("data") if isinstance(raw.get("data"), dict) else None
            audio_hex = data_dict.get("audio") if data_dict else None
            extra_info = raw.get("extra_info") or {}
            audio_format = (extra_info.get("audio_format") if isinstance(extra_info, dict) else None) or "mp3"
            audio_length_ms = extra_info.get("audio_length") if isinstance(extra_info, dict) else None
            size_bytes = 0
            if audio_hex:
                try:
                    size_bytes = len(bytes.fromhex(audio_hex))
                except Exception:
                    size_bytes = 0
            success = bool(audio_hex and size_bytes > 0)
            results.append(make_result(
                model_id=model_id, family="speech", capability_id="tts-sync",
                protocol="native", scope="model_level",
                status="success" if success else "failed",
                http_status=200, latency_ms=round(latency_ms, 1),
                output_present=success,
                extra={
                    "audio_format": audio_format,
                    "asset_size": size_bytes,
                    "audio_length_ms": audio_length_ms,
                    "hex_decode_ok": size_bytes > 0,
                },
            ))
            print(f"{'OK' if success else 'FAILED'} ({latency_ms:.0f}ms) size={size_bytes}B fmt={audio_format}")
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(make_result(
                model_id=model_id, family="speech", capability_id="tts-sync",
                protocol="native", scope="model_level", status="failed",
                latency_ms=round(latency_ms, 1),
                error_type=type(exc).__name__, error_message=str(exc),
            ))
            print(f"FAILED ({latency_ms:.0f}ms) {exc}")
    return results


# ── Image probe ────────────────────────────────────────────────────────────────

def probe_image(native_client: MiniMaxNativeClient, dry_run: bool = False) -> list[dict]:
    results = []
    for model_id in IMAGE_MODELS:
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
            "n": 1,
        }
        start = time.perf_counter()
        try:
            raw = native_client.image_generation(payload)
            latency_ms = (time.perf_counter() - start) * 1000
            img_data = raw.get("data") if isinstance(raw.get("data"), dict) else None
            image_urls = img_data.get("image_urls") if img_data else None
            metadata = raw.get("metadata") or {}
            url_count = len(image_urls) if image_urls else 0
            success_count = metadata.get("success_count", 0) if isinstance(metadata, dict) else 0
            failed_count = metadata.get("failed_count", 0) if isinstance(metadata, dict) else 0
            success = bool(image_urls and success_count >= 1)
            results.append(make_result(
                model_id=model_id, family="image", capability_id="image-t2i",
                protocol="native", scope="model_level",
                status="success" if success else "failed",
                http_status=200, latency_ms=round(latency_ms, 1),
                output_present=success,
                extra={
                    "image_urls_count": url_count,
                    "first_image_url_present": bool(image_urls and len(image_urls) > 0),
                    "success_count": success_count,
                    "failed_count": failed_count,
                },
            ))
            print(f"{'OK' if success else 'FAILED'} ({latency_ms:.0f}ms) urls={url_count} ok={success_count}")
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(make_result(
                model_id=model_id, family="image", capability_id="image-t2i",
                protocol="native", scope="model_level", status="failed",
                latency_ms=round(latency_ms, 1),
                error_type=type(exc).__name__, error_message=str(exc),
            ))
            print(f"FAILED ({latency_ms:.0f}ms) {exc}")
    return results


# ── Music probe ────────────────────────────────────────────────────────────────

def probe_music(native_client: MiniMaxNativeClient, dry_run: bool = False) -> list[dict]:
    results = []
    model_id = "music-2.6"
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
        img_data = raw.get("data") if isinstance(raw.get("data"), dict) else None
        audio_url = img_data.get("audio_url") or img_data.get("music_url") if img_data else None
        audio_hex = img_data.get("audio") if img_data else None
        extra_info = raw.get("extra_info") or {}
        audio_format = (extra_info.get("audio_format") if isinstance(extra_info, dict) else None) or "mp3"
        duration_ms = extra_info.get("music_duration") if isinstance(extra_info, dict) else None
        size_bytes = 0
        if audio_hex:
            try:
                size_bytes = len(bytes.fromhex(audio_hex))
            except Exception:
                size_bytes = 0
        has_url = bool(audio_url)
        has_hex = bool(audio_hex and size_bytes > 0)
        success = has_url or has_hex
        results.append(make_result(
            model_id=model_id, family="music", capability_id="music-gen",
            protocol="native", scope="model_level",
            status="success" if success else "failed",
            http_status=200, latency_ms=round(latency_ms, 1),
            output_present=success,
            extra={
                "audio_url_present": has_url,
                "audio_hex_present": has_hex,
                "audio_format": audio_format,
                "asset_size": size_bytes,
                "duration_ms": duration_ms,
            },
        ))
        print(f"{'OK' if success else 'FAILED'} ({latency_ms:.0f}ms) url={has_url} hex={has_hex}")
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        results.append(make_result(
            model_id=model_id, family="music", capability_id="music-gen",
            protocol="native", scope="model_level", status="failed",
            latency_ms=round(latency_ms, 1),
            error_type=type(exc).__name__, error_message=str(exc),
        ))
        print(f"FAILED ({latency_ms:.0f}ms) {exc}")
    return results


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MiniMax model-level probe script")
    parser.add_argument("--scope", default="low-cost", help="Scope: low-cost (default), chat, speech, image, music, dry-run")
    parser.add_argument("--chat", action="store_true", help="Only probe chat models")
    parser.add_argument("--speech", action="store_true", help="Only probe speech models")
    parser.add_argument("--image", action="store_true", help="Only probe image models")
    parser.add_argument("--music", action="store_true", help="Only probe music models")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    dry_run = args.dry_run or args.scope == "dry-run"

    print(f"[probe_model_level_support] scope={args.scope} dry={dry_run}")
    print()

    if not dry_run:
        env = _load_env()
        api_key = env.get("MINIMAX_TOKEN_PLAN_KEY") or env.get("MINIMAX_API_KEY", "")
        if not api_key:
            print("ERROR: API key not configured", file=sys.stderr)
            sys.exit(1)
        group_id = env.get("MINIMAX_GROUP_ID") or None
        native_client = MiniMaxNativeClient(
            api_key=api_key,
            timeout=120.0,
            group_id=group_id,
        )
    else:
        api_key = ""
        group_id = None
        native_client = None  # type: ignore[assignment]

    all_results: list[dict] = []

    scope_chat = args.chat or args.scope in ("low-cost", "chat")
    scope_speech = args.speech or args.scope in ("low-cost", "speech")
    scope_image = args.image or args.scope in ("low-cost", "image")
    scope_music = args.music or args.scope in ("low-cost", "music")

    if scope_chat:
        print("[chat-openai]")
        all_results.extend(probe_chat_openai(api_key, group_id, dry_run))
        print()
        print("[chat-anthropic]")
        all_results.extend(probe_chat_anthropic(api_key, group_id, dry_run))
        print()

    if scope_speech:
        print("[tts-sync]")
        all_results.extend(probe_speech(native_client, dry_run))
        print()

    if scope_image:
        print("[image-t2i]")
        all_results.extend(probe_image(native_client, dry_run))
        print()

    if scope_music:
        print("[music-gen]")
        all_results.extend(probe_music(native_client, dry_run))
        print()

    success = sum(1 for r in all_results if r["probe_status"] == "success")
    failed = sum(1 for r in all_results if r["probe_status"] == "failed")
    skipped = sum(1 for r in all_results if r["probe_status"] == "skipped")

    print(f"Results: {success} success, {failed} failed, {skipped} skipped ({len(all_results)} total)")

    if not dry_run:
        report = {
            "generated_at": ts(),
            "scope": args.scope,
            "summary": {
                "total": len(all_results),
                "success": success,
                "failed": failed,
                "skipped": skipped,
            },
            "results": all_results,
        }
        json_path = RUNTIME_REPORTS_DIR / "model_level_probe_report.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"JSON report -> {json_path}")

        if failed > 0:
            print("\nFailed probes:")
            for r in all_results:
                if r["probe_status"] == "failed":
                    print(f"  {r['model_id']} ({r['capability_id']}): {r['error_type']} -- {r['error_message']}")


if __name__ == "__main__":
    main()
