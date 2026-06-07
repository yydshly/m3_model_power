"""Capability Profile loader — 能力画像数据加载。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent
PROFILES_FILE = DATA_DIR / "capability_profiles.json"


def _load_json() -> dict[str, Any]:
    """加载 profiles JSON 文件，不存在时返回空结构。"""
    if not PROFILES_FILE.exists():
        return {"schema_version": 1, "profiles": {}}
    with PROFILES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_capability_profiles() -> dict[str, Any]:
    """返回全部 profiles 数据。"""
    return _load_json()


def get_capability_profile(family: str) -> dict[str, Any] | None:
    """返回指定 family 的 profile，不存在时返回 None。"""
    data = load_capability_profiles()
    return data.get("profiles", {}).get(family)
