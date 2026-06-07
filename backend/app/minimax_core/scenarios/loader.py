"""Capability Scenario loader — 使用场景数据加载。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent
SCENARIOS_FILE = DATA_DIR / "capability_scenarios.json"


def _load_json() -> dict[str, Any]:
    """加载 scenarios JSON 文件，不存在时返回空结构。"""
    if not SCENARIOS_FILE.exists():
        return {"schema_version": 1, "scenarios": {}}
    with SCENARIOS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_capability_scenarios() -> dict[str, Any]:
    """返回全部 scenarios 数据。"""
    return _load_json()


def get_capability_scenario(scenario_id: str) -> dict[str, Any] | None:
    """返回指定 scenario_id 的场景，不存在时返回 None。"""
    data = load_capability_scenarios()
    return data.get("scenarios", {}).get(scenario_id)
