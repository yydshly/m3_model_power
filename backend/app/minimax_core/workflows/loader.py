"""Capability Workflow loader — 能力流程数据加载。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent
WORKFLOWS_FILE = DATA_DIR / "capability_workflows.json"


def _load_json() -> dict[str, Any]:
    """加载 workflows JSON 文件，不存在时返回空结构。"""
    if not WORKFLOWS_FILE.exists():
        return {"schema_version": 1, "workflows": {}}
    with WORKFLOWS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_capability_workflows() -> dict[str, Any]:
    """返回全部 workflows 数据。"""
    return _load_json()


def get_capability_workflow(workflow_id: str) -> dict[str, Any] | None:
    """返回指定 workflow_id 的流程，不存在时返回 None。"""
    data = load_capability_workflows()
    return data.get("workflows", {}).get(workflow_id)
