"""Capability Workflow API。"""
from __future__ import annotations

from fastapi import APIRouter

from ..minimax_core.workflows import get_capability_workflow, load_capability_workflows

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("")
async def list_workflows() -> dict:
    """返回全部 capability workflows。"""
    data = load_capability_workflows()
    return {
        "schema_version": data.get("schema_version", 1),
        "workflows": data.get("workflows", {}),
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> dict:
    """返回指定 workflow_id 的流程，不存在时 workflow 为 null。"""
    workflow = get_capability_workflow(workflow_id)
    return {
        "id": workflow_id,
        "workflow": workflow,
    }
