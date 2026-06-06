"""
minimax_core.registry — YAML 配置 → 规格对象的加载与查询层。

对外暴露：
    load_yaml_configs  — 加载并转换 config YAML
    ModelRegistry      — 模型注册表
    CapabilityRegistry — 能力注册表
"""
from __future__ import annotations

from .loader import load_yaml_configs, YAMLConfig
from .model_registry import ModelRegistry
from .capability_registry import CapabilityRegistry

__all__ = [
    "load_yaml_configs",
    "YAMLConfig",
    "ModelRegistry",
    "CapabilityRegistry",
]
