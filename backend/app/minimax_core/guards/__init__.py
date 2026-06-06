"""minimax_core.guards — 可复用的防护与工具函数。"""
from __future__ import annotations

from .redaction import redact_key, redact_url
from .risk_gate import (
    evaluate_capability_risk,
    capability_requires_any_confirmation,
    get_required_confirmations,
    CONFIRM_PAID,
    CONFIRM_HIGH_COST,
    CONFIRM_DESTRUCTIVE,
    CONFIRM_ASSET_SOURCE,
    CONFIRM_LONG_RUNNING,
    CONFIRM_EXISTING_TASK,
    CONFIRM_QUOTA,
    ALL_CONFIRM_TYPES,
    RiskGateDecision,
)

__all__ = [
    "redact_key",
    "redact_url",
    "evaluate_capability_risk",
    "capability_requires_any_confirmation",
    "get_required_confirmations",
    "RiskGateDecision",
    "CONFIRM_PAID",
    "CONFIRM_HIGH_COST",
    "CONFIRM_DESTRUCTIVE",
    "CONFIRM_ASSET_SOURCE",
    "CONFIRM_LONG_RUNNING",
    "CONFIRM_EXISTING_TASK",
    "CONFIRM_QUOTA",
    "ALL_CONFIRM_TYPES",
]
