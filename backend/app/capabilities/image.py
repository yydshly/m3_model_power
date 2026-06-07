"""文/图生图。上游同一端点，由 payload 区分。"""
from typing import Any

from ..minimax.client import post_json
from ..minimax_core.contracts.provider_payload import strip_control_fields
from ..registry import register_handler


@register_handler("image-t2i")
async def image_t2i(payload: dict) -> Any:
    provider_payload = strip_control_fields(payload)
    return await post_json("/v1/image_generation", provider_payload, with_group=True, timeout=180)


@register_handler("image-i2i")
async def image_i2i(payload: dict) -> Any:
    provider_payload = strip_control_fields(payload)
    return await post_json("/v1/image_generation", provider_payload, with_group=True, timeout=180)
