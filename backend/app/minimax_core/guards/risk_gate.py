"""RiskGate — 能力执行前强制确认门禁。

规则：只要满足以下任意条件，就必须阻断自动执行，除非用户显式确认：

  billing_policy.requires_explicit_confirmation == true
  operation_policy.requires_operation_confirmation == true
  billing_policy.may_charge_extra == true
  operation_policy.is_destructive == true
  operation_policy.requires_uploaded_asset == true
  operation_policy.is_long_running == true
  operation_policy.requires_existing_task == true

确认项（confirm_*）：
  confirm_paid           — 付费确认（may_charge_extra=true）
  confirm_high_cost      — 高成本确认（billing_category=high_cost_confirm_required）
  confirm_destructive    — 破坏性操作确认（is_destructive=true）
  confirm_asset_source   — 素材来源确认（requires_uploaded_asset=true）
  confirm_long_running   — 长任务确认（is_long_running=true）
  confirm_existing_task  — 已有任务确认（requires_existing_task=true）
  confirm_quota          — 配额确认（tts-async 字符数超阈值）

用法：
    from app.minimax_core.guards.risk_gate import evaluate_capability_risk

    decision = evaluate_capability_risk(capability, confirmations={"confirm_paid": True})
    if not decision.allowed:
        print(decision.blocked_reasons)
"""
from __future__ import annotations

from typing import Any

from ..contracts.specs import CapabilitySpec

# 确认项常量
CONFIRM_PAID = "confirm_paid"
CONFIRM_HIGH_COST = "confirm_high_cost"
CONFIRM_DESTRUCTIVE = "confirm_destructive"
CONFIRM_ASSET_SOURCE = "confirm_asset_source"
CONFIRM_LONG_RUNNING = "confirm_long_running"
CONFIRM_EXISTING_TASK = "confirm_existing_task"
CONFIRM_QUOTA = "confirm_quota"

ALL_CONFIRM_TYPES = {
    CONFIRM_PAID,
    CONFIRM_HIGH_COST,
    CONFIRM_DESTRUCTIVE,
    CONFIRM_ASSET_SOURCE,
    CONFIRM_LONG_RUNNING,
    CONFIRM_EXISTING_TASK,
    CONFIRM_QUOTA,
}


class RiskGateDecision:
    """RiskGate 评估结果。"""

    __slots__ = ("allowed", "blocked_reasons", "required_confirmations", "warnings")

    def __init__(
        self,
        allowed: bool,
        blocked_reasons: list[str],
        required_confirmations: list[str],
        warnings: list[str],
    ) -> None:
        self.allowed = allowed
        self.blocked_reasons = blocked_reasons
        self.required_confirmations = required_confirmations
        self.warnings = warnings

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocked_reasons": self.blocked_reasons,
            "required_confirmations": self.required_confirmations,
            "warnings": self.warnings,
        }


def evaluate_capability_risk(
    capability: CapabilitySpec,
    *,
    confirmations: dict | None = None,
    payload: dict | None = None,
) -> RiskGateDecision:
    """评估能力风险，判断是否允许执行。

    Args:
        capability: CapabilitySpec 实例
        confirmations: 确认项字典，key 为确认类型，value 为 bool
        payload: 调用 payload，用于 tts-async 字符数判断

    Returns:
        RiskGateDecision
    """
    confirmations = confirmations or {}
    payload = payload or {}

    blocked_reasons: list[str] = []
    required_confirmations: list[str] = []
    warnings: list[str] = []

    bp = capability.billing_policy
    op = capability.operation_policy

    # ── 1. tts-async 字符数保护（特殊逻辑：优先级最高）────────────────────
    if capability.id == "tts-async":
        text = payload.get("text", "") or ""
        text_length = len(text)

        max_default_chars = op.max_default_chars
        requires_confirm_above = op.requires_confirmation_above_chars
        hard_block_above = op.hard_block_above_chars_without_confirm

        # <= max_default_chars → 允许（无需确认）
        if max_default_chars is not None and text_length > max_default_chars:
            warnings.append(
                f"tts-async text length {text_length} exceeds default limit {max_default_chars}"
            )

        if requires_confirm_above is not None and text_length > requires_confirm_above:
            if not confirmations.get(CONFIRM_QUOTA, False):
                blocked_reasons.append(
                    f"tts-async: text_length={text_length} > requires_confirmation_above_chars={requires_confirm_above} "
                    f"but confirm_quota=false"
                )
                required_confirmations.append(CONFIRM_QUOTA)

        if hard_block_above is not None and text_length > hard_block_above:
            if not confirmations.get(CONFIRM_QUOTA, False):
                blocked_reasons.append(
                    f"tts-async: text_length={text_length} > hard_block_above_chars_without_confirm={hard_block_above} "
                    f"and confirm_quota=false — hard blocked"
                )
                required_confirmations.append(CONFIRM_QUOTA)

        # tts-async 的 is_long_running 保护由字符数逻辑覆盖，不再单独阻断
    else:
        # ── 2. 长任务确认（is_long_running）──────────────────────────────────
        if op.is_long_running and not confirmations.get(CONFIRM_LONG_RUNNING, False):
            blocked_reasons.append(
                f"{capability.id}: operation_policy.is_long_running=true but confirm_long_running=false"
            )
            required_confirmations.append(CONFIRM_LONG_RUNNING)

    # ── 3. 付费确认（may_charge_extra）─────────────────────────────────────────
    if bp.may_charge_extra and not confirmations.get(CONFIRM_PAID, False):
        blocked_reasons.append(
            f"{capability.id}: billing_policy.may_charge_extra=true but confirm_paid=false"
        )
        required_confirmations.append(CONFIRM_PAID)

    # ── 4. 高成本确认（billing_category=high_cost_confirm_required）────────────
    if bp.billing_category == "high_cost_confirm_required" and not confirmations.get(
        CONFIRM_HIGH_COST, False
    ):
        blocked_reasons.append(
            f"{capability.id}: billing_category=high_cost_confirm_required but confirm_high_cost=false"
        )
        required_confirmations.append(CONFIRM_HIGH_COST)

    # ── 5. 破坏性确认（is_destructive）────────────────────────────────────────
    if op.is_destructive and not confirmations.get(CONFIRM_DESTRUCTIVE, False):
        blocked_reasons.append(
            f"{capability.id}: operation_policy.is_destructive=true but confirm_destructive=false"
        )
        required_confirmations.append(CONFIRM_DESTRUCTIVE)

    # ── 6. 素材来源确认（requires_uploaded_asset）─────────────────────────────
    if op.requires_uploaded_asset and not confirmations.get(CONFIRM_ASSET_SOURCE, False):
        blocked_reasons.append(
            f"{capability.id}: operation_policy.requires_uploaded_asset=true but confirm_asset_source=false"
        )
        required_confirmations.append(CONFIRM_ASSET_SOURCE)

    # ── 7. 已有任务确认（requires_existing_task）──────────────────────────────
    if op.requires_existing_task:
        task_id = payload.get("task_id") or payload.get("file_id")
        if not task_id:
            blocked_reasons.append(
                f"{capability.id}: operation_policy.requires_existing_task=true but no task_id/file_id in payload"
            )
            required_confirmations.append(CONFIRM_EXISTING_TASK)

    allowed = len(blocked_reasons) == 0
    return RiskGateDecision(
        allowed=allowed,
        blocked_reasons=blocked_reasons,
        required_confirmations=required_confirmations,
        warnings=warnings,
    )


def capability_requires_any_confirmation(capability: CapabilitySpec) -> bool:
    """快速判断能力是否需要任意确认项。"""
    if capability.id == "tts-async":
        return True
    bp = capability.billing_policy
    op = capability.operation_policy

    if bp.may_charge_extra:
        return True
    if bp.billing_category == "high_cost_confirm_required":
        return True
    if bp.requires_explicit_confirmation:
        return True
    if op.is_destructive:
        return True
    if op.requires_uploaded_asset:
        return True
    if op.is_long_running:
        return True
    if op.requires_existing_task:
        return True
    return False


def get_required_confirmations(capability: CapabilitySpec) -> list[str]:
    """获取能力需要的确认项列表。"""
    bp = capability.billing_policy
    op = capability.operation_policy
    required: list[str] = []

    if capability.id == "tts-async":
        required.append(CONFIRM_QUOTA)
    else:
        if op.is_long_running:
            required.append(CONFIRM_LONG_RUNNING)
        if bp.may_charge_extra:
            required.append(CONFIRM_PAID)
        if bp.billing_category == "high_cost_confirm_required":
            required.append(CONFIRM_HIGH_COST)
        if op.is_destructive:
            required.append(CONFIRM_DESTRUCTIVE)
        if op.requires_uploaded_asset:
            required.append(CONFIRM_ASSET_SOURCE)
        if op.requires_existing_task:
            required.append(CONFIRM_EXISTING_TASK)

    return required
