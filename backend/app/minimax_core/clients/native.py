"""Native 协议客户端（MiniMax 特色能力）。

覆盖端点：
  TTS       /v1/t2a_v2  (同步)
  Voice     /v1/get_voice
  Image     /v1/image_generation
  Video     /v1/video_generation  (占位，不执行)
  Music     /v1/music_generation
  Lyrics    /v1/lyrics_generation

本轮只实现已验收的 medium 能力（tts-sync / image-t2i / lyrics-gen / music-gen）。
high/video/voice-clone 保留接口占位，不执行真实调用。
"""
from __future__ import annotations

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
