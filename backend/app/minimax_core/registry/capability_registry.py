"""CapabilityRegistry — 能力注册表。

过滤规则与 app/registry/loader.py Registry.models_for_capability 完全对齐：

  chat-openai:
    family == chat AND protocols 包含 openai AND enabled

  chat-anthropic:
    family == chat AND protocols 包含 anthropic AND enabled

  chat-responses-create / chat-responses-tokens:
    family == chat AND protocols 包含 responses AND enabled

  tts-sync / tts-ws / tts-async:
    family == speech AND enabled

  image-t2i / image-i2i:
    family == image AND enabled

  video-t2v / video-i2v / video-s2v:
    family == video AND enabled

  lyrics-gen:
    family == music OR capabilities 包含 lyrics-gen AND enabled

  music-gen:
    family == music AND capabilities 包含 music-gen AND enabled

  music-cover-prep:
    family == music AND capabilities 包含 music-cover-prep AND enabled

  file-*:
    不返回任何模型（category == files）

  legacy / deprecated / enabled=false 默认不进入下拉，
  但 models_for_capability 返回所有匹配项（供前端灰度展示），
  default_model_for_capability 只取 enabled 的。
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
        """返回支持该能力的所有模型（含禁用的，供前端灰度展示）。

        规则（与 app/registry/loader.py Registry.models_for_capability 完全对齐）：
          1. file-* / models-* 能力不返回任何模型
          2. 显式 capability 绑定：capability_id in m.capabilities → 直接命中
          3. family + protocols：若 model_family 存在，
             且 protocols 非空 → m.family == model_family AND 协议重叠
             且 protocols 为空 → m.family == model_family（任意协议）
          4. legacy/deprecated 不进入下拉（显式绑定例外）
        """
        cap = self.by_id(capability_id)
        if not cap:
            return []

        # file-* / models-* 能力不绑定模型
        if cap.category in ("files", "models"):
            return []

        out: list[ModelSpec] = []
        seen_ids: set[str] = set()

        for m in self._model_reg.all():
            # 1. 显式 capability 绑定（优先级最高）
            if capability_id in m.capabilities:
                if m.id not in seen_ids:
                    out.append(m)
                    seen_ids.add(m.id)
                continue

            # 2. family + protocols 过滤
            if cap.model_family:
                if m.family != cap.model_family:
                    continue
                if cap.protocols:
                    # protocols 非空：要求协议重叠
                    if not any(p in m.protocols for p in cap.protocols):
                        continue
                # protocols 为空：任意协议均可
                # 排除 legacy/deprecated
                if m.tier in ("legacy", "deprecated"):
                    continue
                if m.id not in seen_ids:
                    out.append(m)
                    seen_ids.add(m.id)

        return out

    def default_model_for_capability(self, capability_id: str) -> ModelSpec | None:
        """返回该能力下优先级最高的启用模型（highspeed > flagship > standard）。"""
        all_models = self.models_for_capability(capability_id)
        enabled = [m for m in all_models if m.enabled]
        if not enabled:
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
        enabled.sort(key=lambda m: tier_order.get(m.tier, 99))
        return enabled[0]
