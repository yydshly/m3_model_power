"""语音合成 + 音色相关。"""
import base64
from typing import Any

from ..minimax.client import post_bytes, post_json
from ..minimax_core.invoker import CapabilityInvoker
from ..registry import register_handler


def _load_env() -> dict:
    """Load env from backend/.env (Token Plan Only 模式)."""
    env_path = __file__.resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return {}
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _invoker() -> CapabilityInvoker:
    env = _load_env()
    return CapabilityInvoker(api_key=env.get("MINIMAX_TOKEN_PLAN_KEY", ""))


@register_handler("voice-list")
async def voice_list(payload: dict) -> Any:
    body = {"voice_type": payload.get("voice_type", "all")}
    return await post_json("/v1/get_voice", body, with_group=True)


@register_handler("voice-delete")
async def voice_delete(payload: dict) -> Any:
    return await post_json("/v1/delete_voice", payload, with_group=True)


@register_handler("voice-design")
async def voice_design(payload: dict) -> Any:
    return await post_json("/v1/voice_design", payload, with_group=True)


@register_handler("voice-clone-do")
async def voice_clone_do(payload: dict) -> Any:
    return await post_json("/v1/voice_clone", payload, with_group=True)


@register_handler("tts-sync")
async def tts_sync(payload: dict) -> Any:
    """同步 T2A —— 上游可能返回 JSON（hex/base64 audio 字段）或音频字节。
    工作台统一返回 JSON：{audio_base64, format, content_type, raw} 便于前端播放。
    """
    body = {**payload}
    data = await post_json("/v1/t2a_v2", body, with_group=True, timeout=180)
    audio_hex = (
        (data.get("data", {}) or {}).get("audio")
        if isinstance(data, dict)
        else None
    )
    if audio_hex:
        try:
            audio_bytes = bytes.fromhex(audio_hex)
            data["audio_base64"] = base64.b64encode(audio_bytes).decode()
            data["audio_format"] = (
                payload.get("audio_setting", {}).get("format", "mp3")
                if isinstance(payload, dict)
                else "mp3"
            )
        except ValueError:
            pass
    return data


@register_handler("tts-ws")
async def tts_ws(payload: dict) -> Any:
    """WebSocket 流式 TTS。

    通过 CapabilityInvoker.invoke_async() 调用，确保在 FastAPI async loop 中正确运行。
    返回 UnifiedResponse 结构（dict 形式）。
    """
    invoker = _invoker()
    response = await invoker.invoke_async("tts-ws", payload)
    return response.model_dump(mode="json")


@register_handler("tts-async")
async def tts_async(payload: dict) -> Any:
    return await post_json("/v1/t2a_async_v2", payload, with_group=True, timeout=60)


# 防止 ruff 报"未使用导入"
__all__ = ["voice_list", "voice_delete", "voice_design", "voice_clone_do", "tts_sync", "tts_ws", "tts_async"]
_ = post_bytes  # 预留供后续可能直接拉字节的接口
