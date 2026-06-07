"""Capability Runner API — guided form-based experience."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..minimax_core.runner import get_runner_template, is_runner_supported, load_runner_templates

router = APIRouter(prefix="/runner", tags=["runner"])


@router.get("/templates")
async def list_templates() -> dict:
    """返回全部 runner 模板。"""
    templates = load_runner_templates()
    return {
        "schema_version": 1,
        "supported": list(templates.keys()),
        "templates": templates,
    }


@router.get("/template/{capability_id}")
async def get_template(capability_id: str) -> dict:
    """返回指定 capability_id 的 runner 模板。"""
    if not is_runner_supported(capability_id):
        raise HTTPException(status_code=404, detail=f"Capability '{capability_id}' is not supported by the runner yet.")
    template = get_runner_template(capability_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template for '{capability_id}' not found.")
    return template
