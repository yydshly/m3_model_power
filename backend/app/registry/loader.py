"""YAML 配置加载器 —— 单一事实来源。

设计原则：
- 配置文件解析失败要立刻报错，不要静默吞掉
- 解析后做一次引用校验：capability.category 必须存在、model.capabilities 必须存在
- 对外只暴露不可变的 Pydantic 模型，避免在业务里被改坏
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

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
    label: str
    desc: str = ""
    doc_url: str = ""
    method: str = "POST"
    mm_path: str = ""
    status: CapabilityStatus = "planned"
    streaming: bool = False
    async_job: bool = False
    multipart: bool = False
    model_family: str | None = None
    protocols: list[str] = Field(default_factory=list)  # 用于过滤模型下拉，如 [openai], [anthropic], [responses]
    tags: list[str] = Field(default_factory=list)
    example: dict = Field(default_factory=dict)
    notes: str = ""
    cost_level: Literal["none", "quota", "low", "medium", "high"] = "quota"
    cost_note: str = ""


class Model(BaseModel):
    id: str
    label: str
    family: str  # chat | speech | image | video | music
    tier: Literal["flagship", "highspeed", "standard", "hd", "turbo", "legacy", "deprecated"] = "standard"
    official_current: bool = False
    live_available: bool | None = None  # null = 未验收，true/false = 验收结果
    subscription_expected: bool | None = None
    enabled: bool = True
    context: int | None = None
    input_modalities: list[str] = Field(default_factory=list)  # text | image | video | audio
    output_modalities: list[str] = Field(default_factory=list)  # text | image | video | audio | music
    protocols: list[str] = Field(default_factory=list)  # openai | anthropic | responses | native
    capabilities: list[str] = Field(default_factory=list)  # 显式 capability id 列表
    supports_tools: bool = False
    supports_thinking: bool = False
    thinking_can_disable: bool = False
    cost_level: Literal["quota", "low", "medium", "high", "unknown"] = "unknown"
    # 发现方式与状态（用于前端展示）
    discovery_method: Literal["models_api", "capability_probe", "manual_official"] | None = None
    discovery_status: Literal["available", "unavailable", "not_applicable", "unknown"] | None = None
    discovery_note: str = ""
    note: str = ""
    quota_eligible: bool = False  # true = 走 TokenPlanPlus 共享配额，false = 单独按用量计费


class Registry(BaseModel):
    categories: list[Category]
    capabilities: list[Capability]
    models: list[Model]

    # --- 查询便捷方法（前端拉一次，不会跨网络重复调用） ---
    def capabilities_by_category(self, cat_id: str) -> list[Capability]:
        return [c for c in self.capabilities if c.category == cat_id]

    def models_for_capability(self, cap_id: str) -> list[Model]:
        cap = next((c for c in self.capabilities if c.id == cap_id), None)
        if cap is None:
            return []
        out: list[Model] = []
        for m in self.models:
            if not m.enabled:
                continue
            # 显式 capability 绑定
            if cap.id in m.capabilities:
                out.append(m)
                continue
            # family 匹配（model_family 存在时）
            if cap.model_family and m.family == cap.model_family:
                # 若 capability 声明了 protocols，只返回协议兼容的模型
                if cap.protocols:
                    matching = [p for p in m.protocols if p in cap.protocols]
                    if matching:
                        out.append(m)
                else:
                    out.append(m)
        return out


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

    # 引用校验
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
    return _build_registry()


def reload_registry() -> Registry:
    get_registry.cache_clear()
    return get_registry()
