"""CapabilityInvoker — 统一能力调用入口。

设计目标：
  - 外部调用者只需传入 api_key 和 payload，无需关心使用哪个 client
  - 返回 UnifiedResponse / UnifiedError，不返回裸 dict
  - 未实现的能力抛出明确的 NotImplementedCapability

支持的能力：
  chat-openai / chat-anthropic / chat-responses-create / chat-responses-tokens,
  tts-sync / image-t2i / lyrics-gen / music-gen,
  file-list / voice-list,
  models-openai-list / models-anthropic-list / models-openai-retrieve / models-anthropic-retrieve

用法：
    invoker = CapabilityInvoker(api_key="sk-...")
    result = invoker.invoke("tts-sync", {"model": "speech-02-turbo", ...})
"""
from __future__ import annotations

from typing import Any

from .contracts import AssetRef, UnifiedError, UnifiedResponse
from .clients.base import MiniMaxBaseClient
from .clients.openai import MiniMaxOpenAIClient
from .clients.anthropic import MiniMaxAnthropicClient
from .clients.native import MiniMaxNativeClient
from .clients.files import MiniMaxFilesClient


class NotImplementedCapability(Exception):
    """能力尚未实现，调用者应捕获并返回明确错误。"""
    def __init__(self, capability_id: str) -> None:
        self.capability_id = capability_id
        super().__init__(f"capability not implemented in invoker: {capability_id}")


class CapabilityInvoker:
    """统一能力调用器。"""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 60.0,
        group_id: str | None = None,
        openai_client: MiniMaxOpenAIClient | None = None,
        anthropic_client: MiniMaxAnthropicClient | None = None,
        native_client: MiniMaxNativeClient | None = None,
        files_client: MiniMaxFilesClient | None = None,
    ) -> None:
        """初始化调用器。

        所有参数均可选：若不传入 client 实例，则使用传入的 api_key
        （或环境变量）自动构造。
        """
        self._api_key = api_key
        self._timeout = timeout
        self._group_id = group_id

        self._openai = openai_client or MiniMaxOpenAIClient(
            api_key=api_key, timeout=timeout, group_id=group_id)
        self._anthropic = anthropic_client or MiniMaxAnthropicClient(
            api_key=api_key, timeout=timeout, group_id=group_id)
        self._native = native_client or MiniMaxNativeClient(
            api_key=api_key, timeout=timeout, group_id=group_id)
        self._files = files_client or MiniMaxFilesClient(
            api_key=api_key, timeout=timeout, group_id=group_id)

    def invoke(self, capability_id: str, payload: dict | None = None) -> UnifiedResponse:
        """统一调用入口，返回 UnifiedResponse。

        成功返回 UnifiedResponse(ok=True, ...)。
        失败统一抛出 UnifiedError，由调用者负责转换。
        未实现的能力抛出 NotImplementedCapability。
        """
        payload = payload or {}

        if capability_id == "chat-openai":
            return self._chat_openai(payload)
        if capability_id == "chat-anthropic":
            return self._chat_anthropic(payload)
        if capability_id == "chat-responses-create":
            return self._chat_responses_create(payload)
        if capability_id == "chat-responses-tokens":
            return self._chat_responses_tokens(payload)
        if capability_id == "tts-sync":
            return self._tts_sync(payload)
        if capability_id == "image-t2i":
            return self._image_t2i(payload)
        if capability_id == "lyrics-gen":
            return self._lyrics_gen(payload)
        if capability_id == "music-gen":
            return self._music_gen(payload)
        if capability_id == "file-list":
            return self._file_list(payload)
        if capability_id == "voice-list":
            return self._voice_list(payload)
        if capability_id == "models-openai-list":
            return self._models_openai_list(payload)
        if capability_id == "models-anthropic-list":
            return self._models_anthropic_list(payload)
        if capability_id == "models-openai-retrieve":
            return self._models_openai_retrieve(payload)
        if capability_id == "models-anthropic-retrieve":
            return self._models_anthropic_retrieve(payload)

        raise NotImplementedCapability(capability_id)

    # ── Chat ──────────────────────────────────────────────────────────────────

    def _chat_openai(self, payload: dict) -> UnifiedResponse:
        raw = self._openai.chat_completions(payload)
        return UnifiedResponse(
            ok=True,
            capability_id="chat-openai",
            model=payload.get("model"),
            output_type="text",
            text=raw.get("choices", [{}])[0].get("message", {}).get("content", ""),
            raw=raw,
        )

    def _chat_anthropic(self, payload: dict) -> UnifiedResponse:
        raw = self._anthropic.messages(payload)
        content = ""
        if isinstance(raw.get("content"), list):
            for block in raw["content"]:
                if block.get("type") == "text":
                    content = block.get("text", "")
                    break
        elif isinstance(raw.get("content"), str):
            content = raw["content"]
        return UnifiedResponse(
            ok=True,
            capability_id="chat-anthropic",
            model=payload.get("model"),
            output_type="text",
            text=content,
            raw=raw,
        )

    def _chat_responses_create(self, payload: dict) -> UnifiedResponse:
        raw = self._openai.responses_create(payload)
        # 多路径文本提取
        text = self._extract_responses_text(raw)
        return UnifiedResponse(
            ok=True,
            capability_id="chat-responses-create",
            model=payload.get("model"),
            output_type="text",
            text=text,
            raw=raw,
        )

    @staticmethod
    def _extract_responses_text(raw: dict) -> str | None:
        """从 Responses API 响应中提取文本。

        路径优先级：
          1. output_text（部分响应格式）
          2. output[i].content[j].text（结构化 output 数组）
          3. 返回 None（保留 raw 供调用方检查）
        """
        # 路径1
        if raw.get("output_text"):
            return raw["output_text"]
        # 路径2
        output = raw.get("output")
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict):
                    content = item.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                return block.get("text")
        return None

    def _chat_responses_tokens(self, payload: dict) -> UnifiedResponse:
        raw = self._openai.responses_input_tokens(payload)
        return UnifiedResponse(
            ok=True,
            capability_id="chat-responses-tokens",
            model=payload.get("model"),
            output_type="json",
            text=None,
            raw=raw,
        )

    # ── TTS ───────────────────────────────────────────────────────────────────

    def _tts_sync(self, payload: dict) -> UnifiedResponse:
        raw = self._native.tts_http(payload)
        extra = raw.get("extra_info") or {}
        audio_format = (extra.get("audio_format") if isinstance(extra, dict) else None) or "mp3"
        data_dict = raw.get("data") if isinstance(raw.get("data"), dict) else None
        audio_hex = data_dict.get("audio") if data_dict else None

        assets: list[AssetRef] = []
        if audio_hex:
            try:
                audio_bytes = bytes.fromhex(audio_hex)
                assets.append(AssetRef(
                    type="audio",
                    format=audio_format,
                    path=None,   # invoker 不写文件，调用者负责
                    url=None,
                    size_bytes=len(audio_bytes),
                    duration_ms=extra.get("audio_length") if isinstance(extra, dict) else None,
                    committed=False,
                ))
            except Exception:
                pass

        return UnifiedResponse(
            ok=True,
            capability_id="tts-sync",
            model=payload.get("model"),
            output_type="audio",
            assets=assets,
            raw=raw,
        )

    # ── Image ────────────────────────────────────────────────────────────────

    def _image_t2i(self, payload: dict) -> UnifiedResponse:
        raw = self._native.image_generation(payload)
        img_data = raw.get("data") if isinstance(raw.get("data"), dict) else None
        image_urls = img_data.get("image_urls") if img_data else None

        assets: list[AssetRef] = []
        if image_urls:
            for url in image_urls:
                assets.append(AssetRef(
                    type="image",
                    format=None,
                    path=None,
                    url=url,
                    size_bytes=None,
                    committed=False,
                ))

        return UnifiedResponse(
            ok=True,
            capability_id="image-t2i",
            model=payload.get("model"),
            output_type="image",
            assets=assets,
            raw=raw,
        )

    # ── Lyrics ──────────────────────────────────────────────────────────────

    def _lyrics_gen(self, payload: dict) -> UnifiedResponse:
        raw = self._native.lyrics_generation(payload)
        return UnifiedResponse(
            ok=True,
            capability_id="lyrics-gen",
            model=None,
            output_type="text",
            text=raw.get("lyrics", ""),
            raw=raw,
        )

    # ── Music ───────────────────────────────────────────────────────────────

    def _music_gen(self, payload: dict) -> UnifiedResponse:
        raw = self._native.music_generation(payload)
        extra = raw.get("extra_info") or {}
        audio_format = (extra.get("audio_format") if isinstance(extra, dict) else None) or "mp3"
        img_data = raw.get("data") if isinstance(raw.get("data"), dict) else None
        audio_url = img_data.get("audio_url") or img_data.get("music_url") if img_data else None
        audio_hex = img_data.get("audio") if img_data else None

        assets: list[AssetRef] = []
        if audio_url:
            assets.append(AssetRef(
                type="audio",
                format=audio_format,
                path=None,
                url=audio_url,
                size_bytes=None,
                duration_ms=extra.get("music_duration") if isinstance(extra, dict) else None,
                committed=False,
            ))
        elif audio_hex:
            try:
                audio_bytes = bytes.fromhex(audio_hex)
                assets.append(AssetRef(
                    type="audio",
                    format=audio_format,
                    path=None,
                    url=None,
                    size_bytes=len(audio_bytes),
                    duration_ms=extra.get("music_duration") if isinstance(extra, dict) else None,
                    committed=False,
                ))
            except Exception:
                pass

        return UnifiedResponse(
            ok=True,
            capability_id="music-gen",
            model=payload.get("model"),
            output_type="music",
            assets=assets,
            raw=raw,
        )

    # ── Files ────────────────────────────────────────────────────────────────

    def _file_list(self, payload: dict | None) -> UnifiedResponse:
        raw = self._files.list_files()
        return UnifiedResponse(
            ok=True,
            capability_id="file-list",
            model=None,
            output_type="json",
            text=None,
            raw=raw,
        )

    # ── Voice ───────────────────────────────────────────────────────────────

    def _voice_list(self, payload: dict | None) -> UnifiedResponse:
        raw = self._native.voice_list(payload)
        return UnifiedResponse(
            ok=True,
            capability_id="voice-list",
            model=None,
            output_type="json",
            text=None,
            raw=raw,
        )

    # ── Models ──────────────────────────────────────────────────────────────

    def _models_openai_list(self, payload: dict) -> UnifiedResponse:
        raw = self._openai.list_models()
        return UnifiedResponse(
            ok=True,
            capability_id="models-openai-list",
            model=None,
            output_type="json",
            text=None,
            assets=[],
            raw=raw,
        )

    def _models_anthropic_list(self, payload: dict) -> UnifiedResponse:
        raw = self._anthropic.list_models()
        return UnifiedResponse(
            ok=True,
            capability_id="models-anthropic-list",
            model=None,
            output_type="json",
            text=None,
            assets=[],
            raw=raw,
        )

    def _models_openai_retrieve(self, payload: dict) -> UnifiedResponse:
        model_id = payload.get("model", "MiniMax-M3")
        raw = self._openai.retrieve_model(model_id)
        return UnifiedResponse(
            ok=True,
            capability_id="models-openai-retrieve",
            model=model_id,
            output_type="json",
            text=None,
            assets=[],
            raw=raw,
        )

    def _models_anthropic_retrieve(self, payload: dict) -> UnifiedResponse:
        model_id = payload.get("model", "MiniMax-M3")
        raw = self._anthropic.retrieve_model(model_id)
        return UnifiedResponse(
            ok=True,
            capability_id="models-anthropic-retrieve",
            model=model_id,
            output_type="json",
            text=None,
            assets=[],
            raw=raw,
        )
