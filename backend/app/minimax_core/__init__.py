"""
minimax_core — MiniMax 可复用能力开发底座。

对外暴露：
    ModelSpec, CapabilitySpec,
    AssetRef, UnifiedResponse, UnifiedError, VerificationResult,
    redact_key, redact_url,
    CapabilityInvoker, NotImplementedCapability

子模块：
    contracts  — 核心数据结构
    guards     — 脱敏、验证等防护工具
    invoker    — 统一能力调用入口
"""
from __future__ import annotations

from . import contracts
from . import guards
from .invoker import CapabilityInvoker, NotImplementedCapability

__all__ = [
    "contracts",
    "guards",
    "CapabilityInvoker",
    "NotImplementedCapability",
    # contracts shortcuts
    "contracts.ModelSpec",
    "contracts.CapabilitySpec",
    "contracts.AssetRef",
    "contracts.UnifiedResponse",
    "contracts.UnifiedError",
    "contracts.VerificationResult",
    # guards shortcuts
    "guards.redact_key",
    "guards.redact_url",
]
