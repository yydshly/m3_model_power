"""三套对话协议 + Token 估算。

非流式直接通过 invoke 走；流式由 routers/stream.py 单独处理。
"""
from typing import Any

from ..minimax.client import post_json
from ..registry import register_handler


@register_handler("chat-anthropic")
async def chat_anthropic(payload: dict) -> Any:
    body = {**payload}
    body.pop("stream", None)  # 非流式入口强制关流
    return await post_json("/anthropic/v1/messages", body, timeout=180)


@register_handler("chat-openai")
async def chat_openai(payload: dict) -> Any:
    body = {**payload}
    body["stream"] = False
    return await post_json("/v1/chat/completions", body, timeout=180)


@register_handler("chat-responses-create")
async def chat_responses(payload: dict) -> Any:
    body = {**payload}
    body["stream"] = False
    return await post_json("/v1/responses", body, timeout=180)


@register_handler("chat-responses-tokens")
async def chat_responses_tokens(payload: dict) -> Any:
    return await post_json("/v1/responses/input_tokens", payload)
