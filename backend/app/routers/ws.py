"""WebSocket 反向代理：tts-ws

前端连接 ws://localhost:8000/api/ws/tts-ws，发送 JSON 任务体；
后端连接上游 wss://api.minimaxi.com/ws/v1/t2a_v2 并双向透传。
鉴权与 group id 仍在后端注入，前端不接触 Key。
"""
from __future__ import annotations

import asyncio

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import settings
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
    await ws.accept()
    reg = get_registry()
    cap = next((c for c in reg.capabilities if c.id == cap_id), None)
    if cap is None or cap_id not in UPSTREAM_MAP:
        await ws.send_json({"error": f"unknown ws capability: {cap_id}"})
        await ws.close()
        return
    if not settings.minimax_api_key:
        await ws.send_json({"error": "MINIMAX_API_KEY 未配置"})
        await ws.close()
        return

    upstream_url = _upstream_ws_url(UPSTREAM_MAP[cap_id])
    headers = [("Authorization", f"Bearer {settings.minimax_api_key}")]

    try:
        async with websockets.connect(upstream_url, additional_headers=headers, max_size=None) as up:
            async def client_to_up() -> None:
                try:
                    while True:
                        msg = await ws.receive_text()
                        await up.send(msg)
                except WebSocketDisconnect:
                    try:
                        await up.close()
                    except Exception:
                        pass

            async def up_to_client() -> None:
                try:
                    async for msg in up:
                        if isinstance(msg, bytes):
                            await ws.send_bytes(msg)
                        else:
                            await ws.send_text(msg)
                except Exception:
                    pass

            await asyncio.gather(client_to_up(), up_to_client())
    except Exception as e:  # noqa: BLE001
        try:
            await ws.send_json({"error": "upstream_error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
