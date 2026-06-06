"""OpenAI / Anthropic 两套模型清单 —— 只读，4 个 capability。"""
from typing import Any

from ..minimax.client import get_json
from ..registry import register_handler


@register_handler("models-openai-list")
async def openai_list(_: dict) -> Any:
    return await get_json("/v1/models")


@register_handler("models-openai-retrieve")
async def openai_retrieve(payload: dict) -> Any:
    model = payload.get("model")
    if not model:
        raise ValueError("缺少参数 model")
    return await get_json(f"/v1/models/{model}")


@register_handler("models-anthropic-list")
async def anthropic_list(_: dict) -> Any:
    return await get_json("/anthropic/v1/models")


@register_handler("models-anthropic-retrieve")
async def anthropic_retrieve(payload: dict) -> Any:
    model = payload.get("model")
    if not model:
        raise ValueError("缺少参数 model")
    return await get_json(f"/anthropic/v1/models/{model}")
