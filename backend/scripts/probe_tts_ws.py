#!/usr/bin/env python3
"""
probe_tts_ws.py — MiniMax TTS WebSocket 流式验收探针

执行范围：tts-ws（低风险专项验收）
Key 来源：MINIMAX_TOKEN_PLAN_KEY（Token Plan Only 模式）

WebSocket 地址：wss://api.minimaxi.com/ws/v1/t2a_v2
模型：speech-02-turbo
文本：OK（极短）

输出：
  backend/runtime/assets/tts_ws_probe/tts_ws_<timestamp>.mp3
  backend/runtime/reports/tts_ws_probe_report.json

统一返回字段：
  status / http_or_ws_status / model / latency_ms /
  audio_chunk_count / audio_bytes / asset_saved / error_type
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
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


# ── WebSocket probe ────────────────────────────────────────────────────────────

async def _probe_tts_ws(
    api_key: str,
    model: str,
    text: str,
    voice_id: str = "female-tianmei",
    speed: float = 1.0,
    sample_rate: int = 32000,
    audio_format: str = "mp3",
) -> dict:
    """执行 tts-ws WebSocket 探针，返回统一结果字典。"""
    import websockets  # pip install websockets

    url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
    # websockets 16+ uses additional_headers (list of tuples or dict-like)
    additional_headers = [
        ("Authorization", f"Bearer {api_key}"),
    ]

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
        "last_event": None,
        "probed_at": ts(),
    }

    audio_parts: list[bytes] = []
    t0 = time.perf_counter()

    try:
        async with websockets.connect(url, additional_headers=additional_headers) as ws:
            ws_latency_ms = (time.perf_counter() - t0) * 1000
            result["http_or_ws_status"] = "connected"
            result["latency_ms"] = round(ws_latency_ms, 1)

            # 发送 task_start 事件
            start_payload = {
                "event": "task_start",
                "model": model,
                "voice_setting": {
                    "voice_id": voice_id,
                    "speed": speed,
                    "vol": 1.0,
                    "pitch": 0,
                },
                "audio_setting": {
                    "sample_rate": sample_rate,
                    "format": audio_format,
                    "bitrate": 128000,
                    "channel": 1,
                },
            }
            await ws.send(json.dumps(start_payload))

            # 接收流式响应
            recv_count = 0
            text_sent = False
            while True:
                try:
                    raw_msg = await asyncio.wait_for(ws.recv(), timeout=60.0)
                    recv_count += 1
                    result["last_event"] = ts()

                    # 解析消息（可能是 str 或 bytes）
                    msg_text = raw_msg if isinstance(raw_msg, str) else raw_msg.decode("utf-8", errors="replace")
                    payload_str = msg_text.strip()

                    try:
                        payload = json.loads(payload_str)
                    except json.JSONDecodeError:
                        # 非 JSON 原始文本
                        result["events_received"].append(f"raw:{payload_str[:80]}")
                        continue

                    evt_type = payload.get("event", "unknown")
                    result["events_received"].append(evt_type)

                    # 调试打印前几个事件
                    if recv_count <= 8:
                        snippet = payload_str[:100]
                        print(f"    [recv #{recv_count}] event={evt_type} msg={snippet}")

                    # 音频数据在 data.audio（hex 字符串）
                    audio_hex = payload.get("data", {}).get("audio") if isinstance(payload.get("data"), dict) else None
                    if audio_hex and isinstance(audio_hex, str):
                        try:
                            audio_parts.append(bytes.fromhex(audio_hex))
                            result["audio_chunk_count"] = len(audio_parts)
                            result["audio_bytes"] = sum(len(p) for p in audio_parts)
                        except Exception:
                            pass

                    # 收到 task_started 后，发送文本
                    if evt_type == "task_started" and not text_sent:
                        await ws.send(json.dumps({"event": "task_continue", "text": text}))
                        await ws.send(json.dumps({"event": "task_finish"}))
                        text_sent = True

                    if evt_type in ("task_finished", "task_done"):
                        result["status"] = "success"
                        break
                    elif evt_type == "task_failed":
                        result["status"] = "failed"
                        result["error_type"] = "ws_task_failed"
                        result["error_message"] = payload.get("message", str(payload))
                        break
                    elif evt_type == "error":
                        result["status"] = "failed"
                        result["error_type"] = "ws_error_event"
                        result["error_message"] = payload.get("message", str(payload))
                        break

                except asyncio.TimeoutError:
                    if audio_parts:
                        # 有音频数据则视为成功
                        result["status"] = "success"
                    else:
                        result["status"] = "failed"
                        result["error_type"] = "ws_timeout"
                        result["error_message"] = "No message received within 60s"
                    break

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        result["latency_ms"] = round(elapsed_ms, 1)
        result["error_type"] = type(exc).__name__
        result["error_message"] = str(exc)

        # 分类 WebSocket 错误
        exc_str = str(exc).lower()
        if "1004" in exc_str or "token" in exc_str or "auth" in exc_str:
            result["error_type"] = "auth_or_token_mismatch"
        elif "timeout" in exc_str or "timed out" in exc_str:
            result["error_type"] = "ws_timeout"
        elif "close" in exc_str:
            result["error_type"] = "ws_closed"

        if result["http_or_ws_status"] is None:
            result["http_or_ws_status"] = "connection_failed"

    # 保存音频到 runtime
    if audio_parts and result["status"] == "success":
        audio_bytes = b"".join(audio_parts)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = RUNTIME_ASSETS / f"tts_ws_{timestamp}.{audio_format}"
        try:
            out_path.write_bytes(audio_bytes)
            result["asset_saved"] = True
            result["asset_path"] = str(out_path.relative_to(BACKEND / "runtime"))
            result["audio_bytes"] = len(audio_bytes)
        except Exception as save_exc:
            result["error_message"] = f"audio_received_but_save_failed: {save_exc}"

    return result


async def probe_tts_ws(
    api_key: str,
    model: str = "speech-02-turbo",
    text: str = "OK",
    voice_id: str = "female-tianmei",
    speed: float = 1.0,
    dry_run: bool = False,
) -> dict:
    """tts-ws probe 入口。dry_run 时打印计划但不执行。"""
    if dry_run:
        return {
            "status": "skipped",
            "http_or_ws_status": "dry-run",
            "model": model,
            "text": text,
            "latency_ms": None,
            "audio_chunk_count": 0,
            "audio_bytes": 0,
            "asset_saved": False,
            "asset_path": None,
            "error_type": None,
            "error_message": "dry-run",
            "probed_at": ts(),
        }

    return await _probe_tts_ws(
        api_key=api_key,
        model=model,
        text=text,
        voice_id=voice_id,
        speed=speed,
    )


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
    print(f"  events_received:     {r.get('events_received', [])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MiniMax TTS WebSocket probe")
    parser.add_argument("--model", default="speech-02-turbo",
                        help="speech model (default: speech-02-turbo)")
    parser.add_argument("--text", default="OK",
                        help="text to synthesize (default: OK)")
    parser.add_argument("--voice-id", default="female-tianmei",
                        help="voice_id (default: female-tianmei)")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = _load_env()
    token_plan_key = env.get("MINIMAX_TOKEN_PLAN_KEY", "")
    if not token_plan_key:
        print("ERROR: MINIMAX_TOKEN_PLAN_KEY 未配置（Token Plan Only 模式）", file=sys.stderr)
        sys.exit(1)

    print(f"[probe_tts_ws] model={args.model} text={args.text!r} key={_redact_key(token_plan_key)} dry={args.dry_run}")

    result = asyncio.run(probe_tts_ws(
        api_key=token_plan_key,
        model=args.model,
        text=args.text,
        voice_id=args.voice_id,
        speed=args.speed,
        dry_run=args.dry_run,
    ))

    print()
    print_result(result)
    print()

    # 保存 JSON 报告
    report_path = RUNTIME_REPORTS / "tts_ws_probe_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"JSON report -> {report_path}")


if __name__ == "__main__":
    main()
