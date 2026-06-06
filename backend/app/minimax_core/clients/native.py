"""Native 协议客户端（MiniMax 特色能力）。

覆盖端点：
  TTS       /v1/t2a_v2  (同步 + WebSocket 流式)
  Voice     /v1/get_voice
  Image     /v1/image_generation
  Video     /v1/video_generation  (占位，不执行)
  Music     /v1/music_generation
  Lyrics    /v1/lyrics_generation

本轮只实现已验收的 medium 能力（tts-sync / tts-ws / image-t2i / lyrics-gen / music-gen）。
high/video/voice-clone 保留接口占位，不执行真实调用。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from .base import MiniMaxBaseClient


class MiniMaxNativeClient(MiniMaxBaseClient):
    """Native 协议客户端（MiniMax 特色 API）。

    base_url = https://api.minimaxi.com/v1
    """

    base_url = "https://api.minimaxi.com/v1"

    # ── TTS ─────────────────────────────────────────────────────────────────

    def tts_http(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/t2a_v2 — 文本转语音同步接口。"""
        return self.request_json("POST", "/t2a_v2", json=payload, timeout=30)

    async def tts_websocket(
        self,
        payload: dict[str, Any],
        *,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """WebSocket /ws/v1/t2a_v2 — 文本转语音流式接口。

        协议（已验证）：
          1. 连接后发送 task_start（model / voice_setting / audio_setting，不含 text）
          2. 收到 task_started 后，发送 task_continue（含 text）和 task_finish
          3. 服务端通过 task_continued JSON 事件在 data.audio 字段返回 hex 音频
          4. 全部音频接收完后收到 task_finished

        返回结构：
          {
            "ok": True,
            "audio_bytes": b"...",
            "audio_chunk_count": int,
            "events": [...],
            "session_id": str,
          }
          失败时抛出异常。
        """
        import websockets

        ws_url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
        additional_headers = [("Authorization", f"Bearer {self.get_api_key()}")]

        model = payload.get("model", "speech-02-turbo")
        text = payload.get("text", "OK")
        voice_id = payload.get("voice_id", "female-tianmei")
        speed = payload.get("speed", 1.0)
        sample_rate = payload.get("sample_rate", 32000)
        audio_format = payload.get("audio_format", "mp3")

        audio_parts: list[bytes] = []
        events: list[str] = []
        session_id: str | None = None

        async with websockets.connect(ws_url, additional_headers=additional_headers) as ws:
            # 发送 task_start（不含 text）
            await ws.send(json.dumps({
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
            }))

            text_sent = False

            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    if audio_parts:
                        # 有音频则视为成功
                        break
                    raise TimeoutError(f"tts-ws timeout after {timeout}s with no audio")

                msg_text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")

                try:
                    evt = json.loads(msg_text.strip())
                except json.JSONDecodeError:
                    events.append(f"raw:{msg_text[:80]}")
                    continue

                evt_type = evt.get("event", "unknown")
                events.append(evt_type)

                if evt_type == "connected_success" or evt_type == "task_started":
                    session_id = evt.get("session_id") or session_id

                # 收到 task_started 后发送文本
                if evt_type == "task_started" and not text_sent:
                    await ws.send(json.dumps({"event": "task_continue", "text": text}))
                    await ws.send(json.dumps({"event": "task_finish"}))
                    text_sent = True

                # 音频在 data.audio hex 字段中
                audio_hex = evt.get("data", {}).get("audio") if isinstance(evt.get("data"), dict) else None
                if audio_hex and isinstance(audio_hex, str):
                    try:
                        audio_parts.append(bytes.fromhex(audio_hex))
                    except Exception:
                        pass

                if evt_type in ("task_finished", "task_done"):
                    break
                if evt_type in ("task_failed", "error"):
                    msg = evt.get("message", str(evt))
                    raise RuntimeError(f"tts-ws error event: {evt_type} — {msg}")

        return {
            "ok": True,
            "audio_bytes": b"".join(audio_parts),
            "audio_chunk_count": len(audio_parts),
            "events": events,
            "session_id": session_id,
        }

    # ── Voice ────────────────────────────────────────────────────────────────

    def voice_list(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST /v1/get_voice — 查询音色列表。"""
        return self.request_json("POST", "/get_voice", json=payload or {"voice_type": "all"})

    # ── Image ───────────────────────────────────────────────────────────────

    def image_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/image_generation — 文生图 / 图生图。"""
        return self.request_json("POST", "/image_generation", json=payload, timeout=30)

    # ── Music ────────────────────────────────────────────────────────────────

    def music_generation(self, payload: dict[str, Any], timeout: float = 180.0) -> dict[str, Any]:
        """POST /v1/music_generation — 音乐生成。"""
        return self.request_json("POST", "/music_generation", json=payload, timeout=timeout)

    # ── Lyrics ──────────────────────────────────────────────────────────────

    def lyrics_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/lyrics_generation — 歌词生成。"""
        return self.request_json("POST", "/lyrics_generation", json=payload, timeout=30)

    # ── Video（占位 — 本轮不执行）────────────────────────────────────────────

    def video_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/video_generation — 视频生成（占位）。"""
        raise NotImplementedError(
            "video_generation is high-cost; this stub prevents accidental execution"
        )

    # ── Voice Clone（占位 — 本轮不执行）──────────────────────────────────────

    def voice_clone(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/voice_clone — 音色克隆（占位）。"""
        raise NotImplementedError(
            "voice_clone is high-cost; this stub prevents accidental execution"
        )

    def voice_design(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/voice_design — 音色设计（占位）。"""
        raise NotImplementedError(
            "voice_design is medium-cost; this stub prevents accidental execution"
        )
