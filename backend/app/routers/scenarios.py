"""Capability Scenario API。"""
from __future__ import annotations

from fastapi import APIRouter

from ..minimax_core.scenarios import get_capability_scenario, load_capability_scenarios

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
async def list_scenarios() -> dict:
    """返回全部 capability scenarios。"""
    data = load_capability_scenarios()
    return {
        "schema_version": data.get("schema_version", 1),
        "scenarios": data.get("scenarios", {}),
    }


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str) -> dict:
    """返回指定 scenario_id 的场景，不存在时 scenario 为 null。"""
    scenario = get_capability_scenario(scenario_id)
    return {
        "id": scenario_id,
        "scenario": scenario,
    }
