"""
minimax_core.registry — YAML 配置 → 规格对象的加载与查询层。

对外暴露：
    load_yaml_configs       — 加载并转换 config YAML（原始字典）
    load_model_specs        — 加载 ModelSpec 列表
    load_capability_specs   — 加载 CapabilitySpec 列表
    get_model_registry      — ModelRegistry 单例（@lru_cache）
    get_capability_registry  — CapabilityRegistry 单例（@lru_cache）
    clear_registry_cache    — 清除缓存（测试/重载用）
    ModelRegistry           — 模型注册表类
    CapabilityRegistry      — 能力注册表类
"""
from __future__ import annotations

from .loader import (
    load_yaml_configs,
    load_model_specs,
    load_capability_specs,
    get_model_registry,
    get_capability_registry,
    clear_registry_cache,
)
from .model_registry import ModelRegistry
from .capability_registry import CapabilityRegistry

__all__ = [
    "load_yaml_configs",
    "load_model_specs",
    "load_capability_specs",
    "get_model_registry",
    "get_capability_registry",
    "clear_registry_cache",
    "ModelRegistry",
    "CapabilityRegistry",
]

