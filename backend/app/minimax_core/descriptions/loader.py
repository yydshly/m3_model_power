"""MiniMax Capability Description Loader.

人类可读的能力说明，不涉及 registry 字段。
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent / "capability_descriptions.json"

_cache: dict | None = None


def load_capability_descriptions() -> dict:
    """加载全部 capability descriptions，文件不存在时返回空结构。"""
    global _cache
    if _cache is not None:
        return _cache
    try:
        data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {"schema_version": 1, "descriptions": {}}
    _cache = data
    return data


def get_capability_description(capability_id: str) -> dict | None:
    """根据 capability_id 返回单个描述，不存在时返回 None。"""
    data = load_capability_descriptions()
    return data.get("descriptions", {}).get(capability_id) or None
