"""YAML 配置加载器 —— backend/config/*.yaml → minimax_core 规格对象。

设计原则：
  - 配置文件解析失败立刻报错，不静默吞掉
  - 解析后做引用校验：capability.category 必须存在
  - 对外只暴露不可变的 Pydantic 模型
  - FastAPI route 不直接读 YAML，统一走这里
  - @lru_cache 保证只解析一次
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..contracts import BillingPolicy, CapabilitySpec, ModelSpec
from .model_registry import ModelRegistry
from .capability_registry import CapabilityRegistry

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"缺少配置文件：{path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} 顶层必须是 mapping")
    return data


def load_yaml_configs() -> dict[str, Any]:
    """加载 backend/config/capabilities.yaml 和 models.yaml，返回原始字典。"""
    caps_doc = _load_yaml(CONFIG_DIR / "capabilities.yaml")
    models_doc = _load_yaml(CONFIG_DIR / "models.yaml")
    return {
        "categories": caps_doc.get("categories", []),
        "capabilities": caps_doc.get("capabilities", []),
        "models": models_doc.get("models", []),
    }


def load_categories() -> list[dict[str, Any]]:
    """返回 categories 列表（原始字典）。"""
    return load_yaml_configs()["categories"]


def load_model_specs() -> list[ModelSpec]:
    """加载并转换为 ModelSpec 列表。"""
    data = load_yaml_configs()
    return [ModelSpec.model_validate(m) for m in data["models"]]


def load_capability_specs() -> list[CapabilitySpec]:
    """加载并转换为 CapabilitySpec 列表（来自 capabilities.yaml）。

    字段映射（capabilities.yaml → CapabilitySpec）：
      id          → id
      label       → name
      category    → category
      mm_path     → endpoint
      method      → method
      model_family → model_family  （新增）
      protocols   → protocols      （新增）
      streaming   → is_streaming
      async_job  → is_async
      multipart   → requires_upload
      cost_level  → cost_level
      doc_url     → doc_url
      status      → status
    """
    data = load_yaml_configs()
    categories = data["categories"]
    capabilities = data["capabilities"]

    cat_ids = {c["id"] for c in categories}
    cap_ids: set[str] = set()

    specs: list[CapabilitySpec] = []

    for raw in capabilities:
        cap_id = raw["id"]

        # 引用校验
        if cap_id in cap_ids:
            raise ValueError(f"capability id 重复：{cap_id}")
        cap_ids.add(cap_id)

        cat = raw.get("category", "")
        if cat and cat not in cat_ids:
            raise ValueError(f"capability {cap_id} 引用了不存在的 category：{cat}")

        method_str = raw.get("method", "POST").upper()
        method_map = {"WS": "WS", "GET": "GET", "POST": "POST"}
        method = method_map.get(method_str, "POST")

        cost_level_map = {"none": "none", "quota": "quota", "low": "low", "medium": "medium", "high": "high"}
        cost_level_str = raw.get("cost_level", "quota")
        cost_level = cost_level_map.get(cost_level_str, "quota")

        status_map = {"implemented": "implemented", "planned": "planned", "unsupported": "unsupported"}
        status_str = raw.get("status", "planned")
        status = status_map.get(status_str, "planned")

        raw_bp = raw.get("billing_policy", {})
        billing_policy = BillingPolicy(
            billing_category=raw_bp.get("billing_category", "normal_token_plan_test"),
            requires_explicit_confirmation=bool(raw_bp.get("requires_explicit_confirmation", False)),
            may_charge_extra=bool(raw_bp.get("may_charge_extra", False)),
            consumes_token_plan_quota=bool(raw_bp.get("consumes_token_plan_quota", True)),
            requires_certification=bool(raw_bp.get("requires_certification", False)),
            requires_uploaded_asset=bool(raw_bp.get("requires_uploaded_asset", False)),
            billing_note=raw_bp.get("billing_note", ""),
            official_pricing_note=raw_bp.get("official_pricing_note", ""),
        )

        spec = CapabilitySpec(
            id=cap_id,
            name=raw.get("label", cap_id),
            category=cat,
            endpoint=raw.get("mm_path", ""),
            method=method,
            protocol=raw.get("protocols", ["native"])[0] if raw.get("protocols") else "native",
            model_family=raw.get("model_family") or None,
            protocols=raw.get("protocols", []),
            supported_models=[],
            default_model=None,
            is_streaming=bool(raw.get("streaming", False)),
            is_async=bool(raw.get("async_job", False)),
            requires_upload=bool(raw.get("multipart", False)),
            cost_level=cost_level,
            doc_url=raw.get("doc_url", ""),
            status=status,
            requires_model=bool(raw.get("requires_model", True)),
            billing_policy=billing_policy,
        )
        specs.append(spec)

    return specs


# ── 单例缓存 ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_model_registry() -> ModelRegistry:
    """返回 ModelRegistry 单例（缓存）。"""
    return ModelRegistry(load_model_specs())


@lru_cache(maxsize=1)
def get_capability_registry() -> CapabilityRegistry:
    """返回 CapabilityRegistry 单例（缓存）。"""
    return CapabilityRegistry(
        capabilities=load_capability_specs(),
        model_registry=get_model_registry(),
    )


@lru_cache(maxsize=1)
def get_categories() -> list[dict[str, Any]]:
    """返回 categories 列表单例（缓存）。"""
    cats = load_categories()
    # 按 order 排序
    cats.sort(key=lambda c: c.get("order", 100))
    return cats


def clear_registry_cache() -> None:
    """清除 registry 缓存（测试/重载用）。"""
    get_model_registry.cache_clear()
    get_capability_registry.cache_clear()
    get_categories.cache_clear()
