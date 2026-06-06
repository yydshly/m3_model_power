"""app/registry/loader — 纯兼容层，全部委托给 minimax_core.registry。

本文件保留旧模块路径、函数名和类型别名，
内部不再直接读取 YAML，而是委托 minimax_core.registry.loader，
并将 ModelSpec/CapabilitySpec 转换为旧 Pydantic 模型。

外部调用不变：
  get_registry()         → Registry（categories/capabilities/models + model_dump()）
  reload_registry()      → 清除缓存
  models_for_capability() → list[Model]（过滤后）
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── 类型别名（供旧代码兼容，不做重复定义）──────────────────────────────────────
# 旧 Pydantic 模型保留在这里作为返回类型
CapabilityStatus = Literal["implemented", "planned", "unsupported"]


class Category(BaseModel):
    id: str
    label: str
    emoji: str = ""
    desc: str = ""
    order: int = 100


class Capability(BaseModel):
    id: str
    category: str
    label: str = ""
    desc: str = ""
    doc_url: str = ""
    method: str = "POST"
    mm_path: str = ""
    status: CapabilityStatus = "planned"
    streaming: bool = False
    async_job: bool = False
    multipart: bool = False
    model_family: str | None = None
    protocols: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    example: dict = Field(default_factory=dict)
    notes: str = ""
    cost_level: Literal["none", "quota", "low", "medium", "high"] = "quota"
    cost_note: str = ""
    requires_model: bool = True


class Model(BaseModel):
    id: str
    label: str
    family: str
    tier: Literal["flagship", "highspeed", "standard", "hd", "turbo", "legacy", "deprecated"] = "standard"
    official_current: bool = False
    live_available: bool | None = None
    subscription_expected: bool | None = None
    enabled: bool = True
    context: int | None = None
    input_modalities: list[str] = Field(default_factory=list)
    output_modalities: list[str] = Field(default_factory=list)
    protocols: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    supports_tools: bool = False
    supports_thinking: bool = False
    thinking_can_disable: bool = False
    cost_level: Literal["quota", "low", "medium", "high", "unknown"] = "unknown"
    discovery_method: Literal["models_api", "capability_probe", "manual_official"] | None = None
    discovery_status: Literal["available", "unavailable", "not_applicable", "unknown"] | None = None
    discovery_note: str = ""
    note: str = ""
    quota_eligible: bool = False


class Registry(BaseModel):
    """兼容层 Registry，内部委托 minimax_core.registry。"""
    categories: list[Category]
    capabilities: list[Capability]
    models: list[Model]

    def capabilities_by_category(self, cat_id: str) -> list[Category]:
        return [c for c in self.categories if c.id == cat_id]

    def models_for_capability(self, cap_id: str) -> list[Model]:
        """与旧逻辑完全对齐：只返回 enabled=True 的模型。"""
        cap = next((c for c in self.capabilities if c.id == cap_id), None)
        if not cap:
            return []
        out: list[Model] = []
        for m in self.models:
            if not m.enabled:
                continue
            if cap_id in m.capabilities:
                out.append(m)
                continue
            if cap.model_family and m.family == cap.model_family:
                if cap.protocols:
                    if any(p in m.protocols for p in cap.protocols):
                        out.append(m)
                else:
                    out.append(m)
        return out


# ── 转换函数 ────────────────────────────────────────────────────────────────

def _spec_to_model(spec) -> Model:
    """minimax_core ModelSpec → 旧 Model"""
    return Model(
        id=spec.id,
        label=spec.label,
        family=spec.family,
        tier=spec.tier,
        official_current=spec.official_current,
        live_available=spec.live_available,
        subscription_expected=spec.subscription_expected,
        enabled=spec.enabled,
        context=spec.context,
        input_modalities=spec.input_modalities,
        output_modalities=spec.output_modalities,
        protocols=spec.protocols,
        capabilities=spec.capabilities,
        supports_tools=spec.supports_tools,
        supports_thinking=spec.supports_thinking,
        thinking_can_disable=spec.thinking_can_disable,
        cost_level=spec.cost_level,
        discovery_method=spec.discovery_method,
        discovery_status=spec.discovery_status,
        discovery_note=spec.discovery_note,
        note=spec.note,
        quota_eligible=spec.quota_eligible,
    )


def _spec_to_capability(spec) -> Capability:
    """minimax_core CapabilitySpec → 旧 Capability"""
    return Capability(
        id=spec.id,
        category=spec.category,
        label=spec.name,
        desc="",
        doc_url=spec.doc_url,
        method=spec.method,
        mm_path=spec.endpoint,
        status=spec.status,
        streaming=spec.is_streaming,
        async_job=spec.is_async,
        multipart=spec.requires_upload,
        model_family=spec.model_family,
        protocols=spec.protocols,
        requires_model=spec.requires_model,
    )


# ── 核心委托 ────────────────────────────────────────────────────────────────

def _build_registry() -> Registry:
    """从 minimax_core 加载并转换为旧 Registry 格式。"""
    from app.minimax_core.registry.loader import get_model_registry, get_capability_registry

    model_reg = get_model_registry()
    cap_reg = get_capability_registry()

    # categories 来自 capabilities.yaml（minimax_core 未暴露 categories，
    # 暂时从 core loader 的原始 YAML 读取）
    from app.minimax_core.registry.loader import load_yaml_configs
    raw = load_yaml_configs()
    categories = [Category.model_validate(c) for c in raw["categories"]]
    categories.sort(key=lambda c: c.order)

    models = [_spec_to_model(m) for m in model_reg.all()]
    capabilities = [_spec_to_capability(c) for c in cap_reg.all()]

    return Registry(
        categories=categories,
        capabilities=capabilities,
        models=models,
    )


@lru_cache(maxsize=1)
def get_registry() -> Registry:
    """返回 Registry 单例（委托 minimax_core.registry）。"""
    return _build_registry()


def reload_registry() -> Registry:
    get_registry.cache_clear()
    # 同时清除 core 缓存
    from app.minimax_core.registry.loader import clear_registry_cache
    clear_registry_cache()
    return get_registry()


def models_for_capability(cap_id: str) -> list[Model]:
    """保留旧函数签名，内部委托 get_registry()。"""
    return get_registry().models_for_capability(cap_id)
