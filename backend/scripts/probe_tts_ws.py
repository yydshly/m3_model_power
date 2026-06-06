#!/usr/bin/env python3
"""
probe_tts_ws.py — MiniMax TTS WebSocket 流式验收探针

执行范围：tts-ws（低风险专项验收）
Key 来源：MINIMAX_TOKEN_PLAN_KEY（Token Plan Only 模式）

本脚本已重构为复用 MiniMaxNativeClient.tts_websocket()。
保留独立 WebSocket 逻辑用于调试目的（DEBUG_MODE 环境变量开启时）。

输出：
  backend/runtime/assets/tts_ws_probe/tts_ws_<timestamp>.mp3
  backend/runtime/reports/tts_ws_probe_report.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time as time_module
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

RUNTIME_ASSETS = BACKEND / "runtime" / "assets" / "tts_ws_probe"
RUNTIME_REPORTS = BACKEND / "runtime" / "reports"
RUNTIME_ASSETS.mkdir(parents=True, exist_ok=True)
RUNTIME_REPORTS.mkdir(parents=True, exist_ok=True)


def ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ── env loading ─────────────────────────────────────────────────────────────────

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


def _redact_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


# ── Probe via MiniMaxNativeClient.tts_websocket() ───────────────────────────────

def probe_via_client(
    api_key: str,
    model: str,
    text: str,
    voice_id: str,
    speed: float,
) -> dict:
    """通过 MiniMaxNativeClient.tts_websocket() 执行探针。"""
    from app.minimax_core.clients.native import MiniMaxNativeClient

    client = MiniMaxNativeClient(api_key=api_key, timeout=60.0)
    payload = {
        "model": model,
        "text": text,
        "voice_id": voice_id,
        "speed": speed,
        "sample_rate": 32000,
        "audio_format": "mp3",
    }

    t0 = time_module.perf_counter()
    try:
        ws_result = asyncio.run(client.tts_websocket(payload, timeout=60.0))
        latency_ms = round((time_module.perf_counter() - t0) * 1000, 1)
    except Exception as exc:
        latency_ms = round((time_module.perf_counter() - t0) * 1000, 1)
        return {
            "status": "failed",
            "http_or_ws_status": "error",
            "model": model,
            "text": text,
            "latency_ms": latency_ms,
            "audio_chunk_count": 0,
            "audio_bytes": 0,
            "asset_saved": False,
            "asset_path": None,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "probed_at": ts(),
        }

    audio_bytes = ws_result.get("audio_bytes", b"")
    audio_chunk_count = ws_result.get("audio_chunk_count", 0)
    events = ws_result.get("events", [])

    # 保存音频
    asset_saved = False
    asset_path = None
    if audio_bytes:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = RUNTIME_ASSETS / f"tts_ws_{timestamp}.mp3"
        try:
            out_path.write_bytes(audio_bytes)
            asset_saved = True
            asset_path = str(out_path.relative_to(BACKEND / "runtime"))
        except Exception as save_exc:
            pass

    return {
        "status": "success",
        "http_or_ws_status": "connected",
        "model": model,
        "text": text,
        "latency_ms": latency_ms,
        "audio_chunk_count": audio_chunk_count,
        "audio_bytes": len(audio_bytes),
        "asset_saved": asset_saved,
        "asset_path": asset_path,
        "error_type": None,
        "error_message": None,
        "events_received": events,
        "session_id": ws_result.get("session_id"),
        "probed_at": ts(),
    }


# ── Standalone WebSocket（调试模式） ───────────────────────────────────────────

async def _probe_ws_standalone(
    api_key: str,
    model: str,
    text: str,
    voice_id: str = "female-tianmei",
    speed: float = 1.0,
) -> dict:
    """独立 WebSocket 实现（DEBUG_MODE 时使用）。"""
    import websockets

    url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
    additional_headers = [("Authorization", f"Bearer {api_key}")]

    result = {
        "status": "failed",
        "http_or_ws_status": None,
        "model": model,
        "text": text,
        "latency_ms": None,
        "audio_chunk_count": 0,
        "audio_bytes": 0,
        "asset_saved": False,
        "asset_path": None,
        "error_type": None,
        "error_message": None,
        "events_received": [],
        "probed_at": ts(),
    }

    audio_parts: list[bytes] = []
    t0 = time_module.perf_counter()

    try:
        async with websockets.connect(url, additional_headers=additional_headers) as ws:
            result["http_or_ws_status"] = "connected"
            result["latency_ms"] = round((time_module.perf_counter() - t0) * 1000, 1)

            await ws.send(json.dumps({
                "event": "task_start",
                "model": model,
                "voice_setting": {"voice_id": voice_id, "speed": speed, "vol": 1.0, "pitch": 0},
                "audio_setting": {"sample_rate": 32000, "format": "mp3", "bitrate": 128000, "channel": 1},
            }))

            text_sent = False
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60.0)
                except asyncio.TimeoutError:
                    result["status"] = "success" if audio_parts else "failed"
                    result["error_type"] = "ws_timeout" if not audio_parts else None
                    break

                msg_text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
                try:
                    evt = json.loads(msg_text.strip())
                except json.JSONDecodeError:
                    continue

                evt_type = evt.get("event", "unknown")
                result["events_received"].append(evt_type)

                audio_hex = evt.get("data", {}).get("audio") if isinstance(evt.get("data"), dict) else None
                if audio_hex and isinstance(audio_hex, str):
                    try:
                        audio_parts.append(bytes.fromhex(audio_hex))
                    except Exception:
                        pass

                if evt_type == "task_started" and not text_sent:
                    await ws.send(json.dumps({"event": "task_continue", "text": text}))
                    await ws.send(json.dumps({"event": "task_finish"}))
                    text_sent = True

                if evt_type in ("task_finished", "task_done"):
                    result["status"] = "success"
                    break
                if evt_type in ("task_failed", "error"):
                    result["status"] = "failed"
                    result["error_type"] = "ws_error"
                    result["error_message"] = evt.get("message", str(evt))
                    break

    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error_message"] = str(exc)
        if result["http_or_ws_status"] is None:
            result["http_or_ws_status"] = "connection_failed"

    if audio_parts and result["status"] == "success":
        audio_bytes = b"".join(audio_parts)
        result["audio_bytes"] = len(audio_bytes)
        result["audio_chunk_count"] = len(audio_parts)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = RUNTIME_ASSETS / f"tts_ws_{timestamp}.mp3"
        try:
            out_path.write_bytes(audio_bytes)
            result["asset_saved"] = True
            result["asset_path"] = str(out_path.relative_to(BACKEND / "runtime"))
        except Exception:
            pass

    return result


# ── print helpers ───────────────────────────────────────────────────────────────

def print_result(r: dict) -> None:
    print(f"  status:              {r['status']}")
    print(f"  http_or_ws_status:   {r['http_or_ws_status']}")
    print(f"  model:               {r['model']}")
    print(f"  text:                {r['text']}")
    print(f"  latency_ms:          {r['latency_ms']}")
    print(f"  audio_chunk_count:   {r['audio_chunk_count']}")
    print(f"  audio_bytes:         {r['audio_bytes']}")
    print(f"  asset_saved:         {r['asset_saved']}")
    print(f"  asset_path:          {r['asset_path']}")
    print(f"  error_type:          {r['error_type']}")
    print(f"  error_message:       {r.get('error_message', '')}")
    print(f"  events:             {r.get('events_received', [])}")


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MiniMax TTS WebSocket probe")
    parser.add_argument("--model", default="speech-02-turbo")
    parser.add_argument("--text", default="OK")
    parser.add_argument("--voice-id", default="female-tianmei")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--debug-ws", action="store_true",
                        help="使用独立 WebSocket 实现而非 core client（调试用）")
    args = parser.parse_args()

    env = _load_env()
    token_plan_key = env.get("MINIMAX_TOKEN_PLAN_KEY", "")
    if not token_plan_key:
        print("ERROR: MINIMAX_TOKEN_PLAN_KEY 未配置（Token Plan Only 模式）", file=sys.stderr)
        sys.exit(1)

    print(f"[probe_tts_ws] model={args.model} text={args.text!r} key={_redact_key(token_plan_key)} "
          f"dry={args.dry_run} debug_ws={args.debug_ws}")

    if args.dry_run:
        result = {
            "status": "skipped", "http_or_ws_status": "dry-run",
            "model": args.model, "text": args.text,
            "latency_ms": None, "audio_chunk_count": 0, "audio_bytes": 0,
            "asset_saved": False, "asset_path": None,
            "error_type": None, "error_message": "dry-run", "probed_at": ts(),
        }
    elif args.debug_ws:
        result = asyncio.run(_probe_ws_standalone(
            api_key=token_plan_key,
            model=args.model,
            text=args.text,
            voice_id=args.voice_id,
            speed=args.speed,
        ))
    else:
        result = probe_via_client(
            api_key=token_plan_key,
            model=args.model,
            text=args.text,
            voice_id=args.voice_id,
            speed=args.speed,
        )

    print()
    print_result(result)
    print()

    report_path = RUNTIME_REPORTS / "tts_ws_probe_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"JSON report -> {report_path}")


if __name__ == "__main__":
    main()
