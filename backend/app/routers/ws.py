"""WebSocket 反向代理：tts-ws

前端通过 /api/ws/tts-ws 连接 Vite dev server，由前端代理转发到后端 8777。
后端连接上游 wss://api.minimaxi.com/ws/v1/t2a_v2 并双向透传。
鉴权与 group id 仍在后端注入，前端不接触 Key。

历史写入（P1-4）：
- 连接关闭后写入摘要到 history.jsonl（不写完整消息和音频）
- 摘要包含 client/upstream message count、audio bytes、model、voice_id、duration_ms
- 终态事件后主动关闭连接，让 finally 立即写入 history
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import settings
from ..minimax_core.verification.diagnostics_store import new_trace_id, append_trace_event
from ..minimax_core.verification.history_store import append_history
from ..registry import get_registry

router = APIRouter()

UPSTREAM_MAP = {
    "tts-ws": "/ws/v1/t2a_v2",
}


def _upstream_ws_url(path: str) -> str:
    base = settings.minimax_base_url.replace("https://", "wss://").replace("http://", "ws://")
    url = f"{base}{path}"
    if settings.minimax_group_id and "GroupId" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}GroupId={settings.minimax_group_id}"
    return url


@router.websocket("/ws/{cap_id}")
async def ws_proxy(ws: WebSocket, cap_id: str) -> None:
    trace_id = ws.query_params.get("trace_id") or new_trace_id("ws")

    append_trace_event(trace_id, "ws_route_entered", capability_id=cap_id, action="ws")

    await ws.accept()
    reg = get_registry()
    cap = next((c for c in reg.capabilities if c.id == cap_id), None)
    if cap is None or cap_id not in UPSTREAM_MAP:
        await ws.send_json({"error": f"unknown ws capability: {cap_id}"})
        await ws.close()
        return
    if not settings.minimax_effective_api_key:
        await ws.send_json({"error": "MINIMAX_TOKEN_PLAN_KEY / MINIMAX_API_KEY 均未配置，请检查 backend/.env"})
        await ws.close()
        return

    upstream_url = _upstream_ws_url(UPSTREAM_MAP[cap_id])
    headers = [("Authorization", f"Bearer {settings.minimax_effective_api_key}")]

    t0 = time.perf_counter()
    stats = {
        "client_message_count": 0,
        "upstream_message_count": 0,
        "audio_bytes": 0,
        "model": None,
        "voice_id": None,
        "task_text_preview": "",
        "finished_ok": False,
        "error_message": None,
        "terminal_seen": False,
        "trace_id": trace_id,
    }

    async def client_to_up() -> None:
        nonlocal stats
        try:
            while True:
                msg = await ws.receive_text()
                stats["client_message_count"] += 1
                # Extract model/voice_id from task_start, text preview from task_continue
                try:
                    obj = json.loads(msg)
                    if obj.get("event") == "task_start":
                        stats["model"] = obj.get("model")
                        vs = obj.get("voice_setting") or {}
                        stats["voice_id"] = vs.get("voice_id")
                    if obj.get("event") == "task_continue":
                        txt = obj.get("text")
                        if isinstance(txt, str):
                            stats["task_text_preview"] = txt[:200]
                except Exception:
                    pass
                await up.send(msg)
        except WebSocketDisconnect:
            try:
                await up.close()
            except Exception:
                pass

    async def up_to_client() -> None:
        nonlocal stats
        try:
            async for msg in up:
                stats["upstream_message_count"] += 1
                if isinstance(msg, bytes):
                    await ws.send_bytes(msg)
                else:
                    # Try to parse event from upstream message for audio_bytes and finish tracking
                    try:
                        obj = json.loads(msg)
                        audio_hex = (obj or {}).get("data", {}).get("audio")
                        if isinstance(audio_hex, str):
                            stats["audio_bytes"] += len(audio_hex) // 2
                        evt = (obj or {}).get("event") or (obj or {}).get("data", {}).get("event")
                        if evt in ("task_finished", "task_finish", "finished"):
                            stats["finished_ok"] = True
                            stats["terminal_seen"] = True
                        if evt == "task_failed":
                            stats["error_message"] = str(obj)
                            stats["terminal_seen"] = True
                    except Exception:
                        pass
                    await ws.send_text(msg)
                # After sending, if terminal event was seen, close both sides and exit
                if stats.get("terminal_seen"):
                    try:
                        await up.close()
                    except Exception:
                        pass
                    try:
                        await ws.close()
                    except Exception:
                        pass
                    break
        except Exception:
            pass

    try:
        async with websockets.connect(upstream_url, additional_headers=headers, max_size=None) as up:
            await asyncio.gather(client_to_up(), up_to_client())
    except Exception as e:  # noqa: BLE001
        stats["error_message"] = str(e)
        try:
            await ws.send_json({"error": "upstream_error", "message": str(e)})
        except Exception:
            pass
    finally:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        try:
            await ws.close()
        except Exception:
            pass
        # Only write history for meaningful connections (had messages or had an error)
        should_write = (
            stats.get("client_message_count", 0) > 0
            or stats.get("upstream_message_count", 0) > 0
            or stats.get("error_message")
        )
        if should_write:
            try:
                append_history(
                    action="ws",
                    capability_id=cap_id,
                    payload={
                        "model": stats.get("model"),
                        "voice_setting": {"voice_id": stats.get("voice_id")},
                        "text_preview": stats.get("task_text_preview"),
                    },
                    confirmations={},
                    result={
                        "ok": bool(stats.get("finished_ok")) and not stats.get("error_message"),
                        "data": {
                            "ws": True,
                            "client_message_count": stats.get("client_message_count"),
                            "upstream_message_count": stats.get("upstream_message_count"),
                            "audio_bytes": stats.get("audio_bytes"),
                        },
                        "error": "ws_error" if stats.get("error_message") else None,
                        "message": stats.get("error_message"),
                    },
                    duration_ms=duration_ms,
                    trace_id=trace_id,
                )
            except Exception as hist_err:
                print(f"[history] ws append failed: {hist_err}", file=sys.stderr)
                traceback.print_exc()
