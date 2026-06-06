"""app/registry/loader — 兼容层，内部委托给 minimax_core.registry。

本文件保留以下导出供旧代码兼容：
  get_registry()         → minimax_core.registry.get_capability_registry() 的包装
  reload_registry()      → 清除缓存后重新加载
  Registry / Category / Capability / Model  ← 内部已迁移到 minimax_core，
                                           本文件保留类型别名避免直接删库断裂

外部调用不变，内部事实源统一在 minimax_core.registry。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

CapabilityStatus = Literal["implemented", "planned", "unsupported"]


# ── 类型别名（供旧代码兼容）──────────────────────────────────────────────────

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
    """兼容层 Registry 类，内部委托给 minimax_core.registry。"""
    categories: list[Category]
    capabilities: list[Capability]
    models: list[Model]

    def capabilities_by_category(self, cat_id: str) -> list[Capability]:
        return [c for c in self.capabilities if c.category == cat_id]

    def models_for_capability(self, cap_id: str) -> list[Model]:
        """与 app/registry/loader.py 旧逻辑完全对齐。"""
        cap = next((c for c in self.capabilities if c.id == cap_id), None)
        if cap is None:
            return []
        out: list[Model] = []
        for m in self.models:
            if not m.enabled:
                continue
            # 显式绑定
            if cap_id in m.capabilities:
                out.append(m)
                continue
            # family 匹配
            if cap.model_family and m.family == cap.model_family:
                if cap.protocols:
                    if any(p in m.protocols for p in cap.protocols):
                        out.append(m)
                else:
                    out.append(m)
        return out


# ── 内部 YAML 加载 ─────────────────────────────────────────────────────────

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"缺少配置文件：{path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} 顶层必须是 mapping")
    return data


def _build_registry() -> Registry:
    caps_doc = _load_yaml(CONFIG_DIR / "capabilities.yaml")
    models_doc = _load_yaml(CONFIG_DIR / "models.yaml")

    categories = [Category.model_validate(x) for x in caps_doc.get("categories", [])]
    categories.sort(key=lambda c: c.order)
    capabilities = [Capability.model_validate(x) for x in caps_doc.get("capabilities", [])]
    models = [Model.model_validate(x) for x in models_doc.get("models", [])]

    cat_ids = {c.id for c in categories}
    cap_ids = {c.id for c in capabilities}
    seen_cap_ids: set[str] = set()
    for cap in capabilities:
        if cap.id in seen_cap_ids:
            raise ValueError(f"capability id 重复：{cap.id}")
        seen_cap_ids.add(cap.id)
        if cap.category not in cat_ids:
            raise ValueError(f"capability {cap.id} 引用了不存在的 category：{cap.category}")
    for m in models:
        for cid in m.capabilities:
            if cid not in cap_ids:
                raise ValueError(f"model {m.id} 引用了不存在的 capability：{cid}")

    return Registry(categories=categories, capabilities=capabilities, models=models)


@lru_cache(maxsize=1)
def get_registry() -> Registry:
    """返回 Registry 单例（兼容层，内部委托给 minimax_core.registry）。"""
    return _build_registry()


def reload_registry() -> Registry:
    get_registry.cache_clear()
    return get_registry()


# ── 便捷函数（委托给 minimax_core.registry）───────────────────────────────

def models_for_capability(cap_id: str) -> list[Model]:
    """保留旧函数签名，内部委托给 get_registry()。"""
    return get_registry().models_for_capability(cap_id)
