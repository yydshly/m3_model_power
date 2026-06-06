"""YAML 配置加载器 —— backend/config/*.yaml → minimax_core 规格对象。

设计原则：
  - 配置文件解析失败立刻报错，不静默吞掉
  - 解析后做引用校验：capability.category 必须存在
  - 对外只暴露不可变的 Pydantic 模型
  - FastAPI route 不直接读 YAML，统一走这里
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..contracts import CapabilitySpec, ModelSpec

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "config"


@dataclass
class YAMLConfig:
    """原始 YAML 解析结果（未转 Pydantic）。"""
    categories: list[dict[str, Any]] = field(default_factory=list)
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    models: list[dict[str, Any]] = field(default_factory=list)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"缺少配置文件：{path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} 顶层必须是 mapping")
    return data


def load_yaml_configs() -> YAMLConfig:
    """加载 backend/config/capabilities.yaml 和 models.yaml，返回原始字典。"""
    caps_doc = _load_yaml(CONFIG_DIR / "capabilities.yaml")
    models_doc = _load_yaml(CONFIG_DIR / "models.yaml")

    return YAMLConfig(
        categories=caps_doc.get("categories", []),
        capabilities=caps_doc.get("capabilities", []),
        models=models_doc.get("models", []),
    )


def load_model_specs() -> list[ModelSpec]:
    """加载并转换为 ModelSpec 列表。"""
    cfg = load_yaml_configs()
    return [ModelSpec.model_validate(m) for m in cfg.models]


def load_capability_specs() -> list[CapabilitySpec]:
    """加载并转换为 CapabilitySpec 列表（来自 capabilities.yaml）。

    注意：capabilities.yaml 的字段与 CapabilitySpec 并非完全一一对应，
    此处做字段映射以适配。
    """
    cfg = load_yaml_configs()

    # 能力 YAML 字段 → CapabilitySpec 字段映射
    specs: list[CapabilitySpec] = []
    cap_ids: set[str] = set()

    for raw in cfg.capabilities:
        cap_id = raw["id"]

        # 引用校验
        if cap_id in cap_ids:
            raise ValueError(f"capability id 重复：{cap_id}")
        cap_ids.add(cap_id)

        # category 引用 categories.yaml 中的 id 列表
        cat_ids = {c["id"] for c in cfg.categories}
        if raw.get("category") and raw["category"] not in cat_ids:
            raise ValueError(f"capability {cap_id} 引用了不存在的 category：{raw['category']}")

        # model_family 字段映射
        model_family = raw.get("model_family") or None

        # protocols 字段（capabilities.yaml 用 protocols 列表表示协议过滤）
        protocols_raw = raw.get("protocols", [])
        protocol = protocols_raw[0] if protocols_raw else "native"

        # supported_models（来自 capabilities.yaml 逻辑 — 本轮留空，由 CapabilityRegistry 填充）
        supported_models: list[str] = []

        # endpoint = mm_path
        endpoint = raw.get("mm_path", "")

        # method
        method_map = {"WS": "WS", "GET": "GET", "POST": "POST"}
        method_str = raw.get("method", "POST")
        method = method_map.get(method_str.upper(), "POST")

        # streaming / async
        is_streaming = bool(raw.get("streaming", False))
        is_async = bool(raw.get("async_job", False))

        # cost_level
        cost_level_map = {"none": "none", "quota": "quota", "low": "low", "medium": "medium", "high": "high"}
        cost_level_str = raw.get("cost_level", "quota")
        cost_level = cost_level_map.get(cost_level_str, "quota")

        # status
        status_map = {"implemented": "implemented", "planned": "planned", "unsupported": "unsupported"}
        status_str = raw.get("status", "planned")
        status = status_map.get(status_str, "planned")

        spec = CapabilitySpec(
            id=cap_id,
            name=raw.get("label", cap_id),
            category=raw.get("category", ""),
            endpoint=endpoint,
            method=method,
            protocol=protocol,
            supported_models=supported_models,
            default_model=None,
            is_streaming=is_streaming,
            is_async=is_async,
            requires_upload=bool(raw.get("multipart", False)),
            cost_level=cost_level,
            doc_url=raw.get("doc_url", ""),
            status=status,
        )
        specs.append(spec)

    return specs
