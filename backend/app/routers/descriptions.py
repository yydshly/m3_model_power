"""Capability Description API — 人类可读的能力说明。"""
from __future__ import annotations

from fastapi import APIRouter

from ..minimax_core.descriptions.loader import get_capability_description, load_capability_descriptions

router = APIRouter(prefix="/descriptions", tags=["descriptions"])


@router.get("/capabilities")
async def list_capability_descriptions() -> dict:
    """返回全部 capability descriptions。"""
    data = load_capability_descriptions()
    return {
        "schema_version": data.get("schema_version", 1),
        "updated_at": data.get("updated_at"),
        "descriptions": data.get("descriptions", {}),
    }


@router.get("/capabilities/{cap_id}")
async def get_capability_description_endpoint(cap_id: str) -> dict:
    """返回指定 capability 的 description，不存在时 description 为 null。"""
    desc = get_capability_description(cap_id)
    return {
        "capability_id": cap_id,
        "description": desc,
    }
