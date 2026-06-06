"""
minimax_core.contracts — 可复用的数据结构定义。

对外暴露：
    ModelSpec, CapabilitySpec, AssetRef,
    UnifiedResponse, UnifiedError, VerificationResult,
    redaction helpers
"""
from __future__ import annotations

from .specs import CapabilitySpec, ModelSpec
from .response import AssetRef, UnifiedError, UnifiedResponse
from .verification import VerificationResult

__all__ = [
    "ModelSpec",
    "CapabilitySpec",
    "AssetRef",
    "UnifiedResponse",
    "UnifiedError",
    "VerificationResult",
]
