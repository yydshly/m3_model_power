"""ModelRegistry — 模型注册表。

查询接口：
  all()                    — 所有模型（含禁用的）
  enabled()                — 仅 enabled=True 的模型
  by_id(id)                — 按模型 id 精确查找
  by_family(family)         — 按 family 过滤（chat / speech / image / video / music）
  by_protocol(protocol)    — 按协议过滤（openai / anthropic / responses / native）
  official_current()        — official_current=True 的模型
  live_available()         — live_available=True 的模型
"""
from __future__ import annotations

from typing import Literal

from ..contracts import ModelSpec


class ModelRegistry:
    """模型注册表。"""

    def __init__(self, models: list[ModelSpec]) -> None:
        self._models = models

    def all(self) -> list[ModelSpec]:
        return list(self._models)

    def enabled(self) -> list[ModelSpec]:
        return [m for m in self._models if m.enabled]

    def by_id(self, model_id: str) -> ModelSpec | None:
        return next((m for m in self._models if m.id == model_id), None)

    def by_family(self, family: str) -> list[ModelSpec]:
        return [m for m in self._models if m.family == family]

    def by_protocol(self, protocol: str) -> list[ModelSpec]:
        return [m for m in self._models if protocol in m.protocols]

    def official_current(self) -> list[ModelSpec]:
        return [m for m in self._models if m.official_current]

    def live_available(self) -> list[ModelSpec]:
        return [m for m in self._models if m.live_available is True]
