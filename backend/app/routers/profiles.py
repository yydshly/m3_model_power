"""Capability Profile API。"""
from __future__ import annotations

from fastapi import APIRouter

from ..minimax_core.profiles import get_capability_profile, load_capability_profiles

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
async def list_profiles() -> dict:
    """返回全部 capability profiles。"""
    data = load_capability_profiles()
    return {
        "schema_version": data.get("schema_version", 1),
        "profiles": data.get("profiles", {}),
    }


@router.get("/{family}")
async def get_profile(family: str) -> dict:
    """返回指定 family 的 profile，不存在时 profile 为 null。"""
    profile = get_capability_profile(family)
    return {
        "family": family,
        "profile": profile,
    }
