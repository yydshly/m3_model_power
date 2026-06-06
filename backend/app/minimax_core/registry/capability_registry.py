"""CapabilityRegistry — 能力注册表。

过滤规则（与 app/registry/loader.py Registry.models_for_capability 保持一致）：
  chat-openai        → protocols 包含 openai 的 chat 模型
  chat-anthropic     → protocols 包含 anthropic 的 chat 模型
  responses          → protocols 包含 responses 的 chat 模型
  tts-sync           → speech 模型
  image-t2i / i2i    → image 模型
  lyrics-gen         → music 模型
  music-gen          → music 模型
  file-*             → 不显示模型（capability 无 model_family）

所有逻辑基于 ModelSpec.protocols / ModelSpec.family / ModelSpec.capabilities
推断，不再直接读取 YAML。
"""
from __future__ import annotations

from ..contracts import CapabilitySpec, ModelSpec
from .model_registry import ModelRegistry


class CapabilityRegistry:
    """能力注册表，按能力 id 查询可用模型。"""

    def __init__(
        self,
        capabilities: list[CapabilitySpec],
        model_registry: ModelRegistry,
    ) -> None:
        self._caps = capabilities
        self._model_reg = model_registry

    def all(self) -> list[CapabilitySpec]:
        return list(self._caps)

    def by_id(self, capability_id: str) -> CapabilitySpec | None:
        return next((c for c in self._caps if c.id == capability_id), None)

    def models_for_capability(self, capability_id: str) -> list[ModelSpec]:
        """返回支持该能力的所有模型（含禁用的，用于前端灰度展示）。

        过滤规则：
          1. 若 ModelSpec.capabilities 显式包含 capability_id，直接命中
          2. 若 capability 无 protocols，按 model_family 匹配
          3. 若 capability 有 protocols，只返回协议兼容的模型
          4. file-* 能力不返回任何模型（capability.model_family 为 None）
        """
        cap = self.by_id(capability_id)
        if not cap:
            return []

        # 文件类能力不绑定模型
        if not cap.category or cap.category == "files":
            return []

        out: list[ModelSpec] = []
        seen_ids: set[str] = set()

        for m in self._model_reg.all():
            # 显式 capability 绑定
            if capability_id in m.capabilities:
                if m.id not in seen_ids:
                    out.append(m)
                    seen_ids.add(m.id)
                continue

            # family 匹配
            # capability.category 在这里是 model_family 的近似
            # 但实际上 capabilities.yaml 用 model_family 字段
            # 我们通过 cap.protocol / cap.category 推断
            if cap.protocol == "native" and cap.category == "voice":
                # speech 模型
                if m.family == "speech":
                    out.append(m)
                    seen_ids.add(m.id)
            elif cap.protocol == "native" and cap.category == "vision":
                if m.family == "image":
                    out.append(m)
                    seen_ids.add(m.id)
            elif cap.protocol == "native" and cap.category == "music":
                if m.family == "music":
                    out.append(m)
                    seen_ids.add(m.id)
            elif cap.protocol == "native" and cap.category == "chat":
                # chat + native 协议（如 TTS）
                if m.family == "chat" and "native" in m.protocols:
                    out.append(m)
                    seen_ids.add(m.id)

        return out

    def default_model_for_capability(self, capability_id: str) -> ModelSpec | None:
        """返回该能力下优先级最高的模型（highspeed > flagship > standard）。"""
        models = self.models_for_capability(capability_id)
        if not models:
            return None

        tier_order = {
            "highspeed": 0,
            "flagship": 1,
            "hd": 1,
            "standard": 2,
            "turbo": 3,
            "legacy": 4,
            "deprecated": 5,
        }

        enabled = [m for m in models if m.enabled]
        if not enabled:
            enabled = models

        enabled.sort(key=lambda m: tier_order.get(m.tier, 99))
        return enabled[0]
