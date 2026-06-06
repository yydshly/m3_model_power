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

    async def tts_async_create(self, payload: dict[str, Any], *, timeout: float = 60.0) -> dict[str, Any]:
        """POST /v1/t2a_async_v2 — 异步 TTS 创建任务。

        成功响应解析：
          - task_id, task_token, file_id, usage_characters
          - base_resp.status_code / status_msg

        失败时抛出异常或返回 ok=False 的 dict。
        """
        raw = await self.request_json_async("POST", "/t2a_async_v2", json=payload, timeout=timeout)

        # 检查业务状态码
        base_resp = raw.get("base_resp") or {}
        status_code = base_resp.get("status_code", 0)
        status_msg = base_resp.get("status_msg")

        if status_code != 0:
            # 非零业务码视为失败
            return {
                "ok": False,
                "base_resp": base_resp,
                "task_id": None,
                "task_token": None,
                "file_id": None,
                "usage_characters": None,
                "raw": raw,
            }

        # 解析关键字段（task_id/token/file_id/usage_characters 在根级别）
        task_id = raw.get("task_id")
        task_token = raw.get("task_token")
        file_id = raw.get("file_id")
        extra_info = raw.get("extra_info") or {}
        usage_characters = raw.get("usage_characters")
        if usage_characters is None and isinstance(extra_info, dict):
            usage_characters = extra_info.get("usage_characters")

        return {
            "ok": True,
            "base_resp": base_resp,
            "task_id": task_id,
            "task_token": task_token,
            "file_id": file_id,
            "usage_characters": usage_characters,
            "raw": raw,
        }

    async def tts_async_query(self, task_id: str | int, *, timeout: float = 30.0) -> dict[str, Any]:
        """GET /v1/query/t2a_async_query_v2?task_id=... — 查询异步任务状态。

        返回字段：
          - task_id, status (Processing / Success / Failed / Expired), file_id
          - base_resp
        """
        params = {"task_id": str(task_id)}
        raw = await self.request_json_async("GET", "/query/t2a_async_query_v2", params=params, timeout=timeout)

        base_resp = raw.get("base_resp") or {}
        status_code = base_resp.get("status_code", 0)

        if status_code != 0:
            return {
                "ok": False,
                "base_resp": base_resp,
                "task_id": str(task_id),
                "status": None,
                "file_id": None,
                "raw": raw,
            }

        # 解析查询结果
        result_data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        status = result_data.get("status") or raw.get("status")
        file_id = result_data.get("file_id") or raw.get("file_id")

        return {
            "ok": True,
            "base_resp": base_resp,
            "task_id": str(task_id),
            "status": status,
            "file_id": file_id,
            "raw": raw,
        }

    async def tts_async_poll(
        self,
        task_id: str | int,
        *,
        interval_seconds: float = 2.0,
        max_attempts: int = 30,
    ) -> dict[str, Any]:
        """轮询异步 TTS 任务直到完成/失败/超时。

        规则：
          - Success  → 返回成功
          - Failed    → 返回 failed
          - Expired   → 返回 expired
          - Processing → 继续轮询
          - 超过 max_attempts → timeout

        返回结构包含：
          - final_status, file_id, poll_attempts, task_info
        """
        import asyncio

        for attempt in range(1, max_attempts + 1):
            query_result = await self.tts_async_query(task_id)

            if not query_result.get("ok"):
                # 查询失败，记录当前 attempt 后返回
                return {
                    "ok": False,
                    "final_status": "query_failed",
                    "file_id": None,
                    "poll_attempts": attempt,
                    "task_id": str(task_id),
                    "task_info": query_result,
                }

            status = query_result.get("status")

            if status == "Success":
                return {
                    "ok": True,
                    "final_status": "Success",
                    "file_id": query_result.get("file_id"),
                    "poll_attempts": attempt,
                    "task_id": str(task_id),
                    "task_info": query_result,
                }
            elif status in ("Failed", "failed"):
                return {
                    "ok": False,
                    "final_status": "Failed",
                    "file_id": query_result.get("file_id"),
                    "poll_attempts": attempt,
                    "task_id": str(task_id),
                    "task_info": query_result,
                }
            elif status in ("Expired", "expired"):
                return {
                    "ok": False,
                    "final_status": "Expired",
                    "file_id": None,
                    "poll_attempts": attempt,
                    "task_id": str(task_id),
                    "task_info": query_result,
                }
            else:
                # Processing / 其他中间态，继续轮询
                if attempt < max_attempts:
                    await asyncio.sleep(interval_seconds)
                    continue
                # 最后一次尝试超时
                return {
                    "ok": False,
                    "final_status": "timeout",
                    "file_id": None,
                    "poll_attempts": attempt,
                    "task_id": str(task_id),
                    "task_info": query_result,
                }

        # 永不触发（兜桥）
        return {
            "ok": False,
            "final_status": "timeout",
            "file_id": None,
            "poll_attempts": max_attempts,
            "task_id": str(task_id),
            "task_info": None,
        }

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
