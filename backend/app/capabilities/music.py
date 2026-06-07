"""音乐 / 歌词。"""
from typing import Any

from ..minimax.client import post_json
from ..minimax_core.contracts.provider_payload import strip_control_fields
from ..registry import register_handler


@register_handler("music-gen")
async def music_gen(payload: dict) -> Any:
    provider_payload = strip_control_fields(payload)
    return await post_json("/v1/music_generation", provider_payload, with_group=True, timeout=240)


@register_handler("lyrics-gen")
async def lyrics_gen(payload: dict) -> Any:
    return await post_json("/v1/lyrics_generation", payload, with_group=True, timeout=60)
