"""provider_payload — 清洗发送给 MiniMax 上游的控制字段。

原则：
  - 不原地修改入参。
  - 只剥离顶层控制字段。
  - 保留所有业务字段。
  - 调用方负责使用清洗后的副本，实际传给 provider。

控制字段（internal confirmation fields，不应发送给上游）：
  confirm_asset_source / confirm_quota / confirm_high_cost /
  confirm_destructive / confirm_long_running / confirm_existing_task /
  confirm_paid / confirm_very_large_quota
"""
from __future__ import annotations

from typing import Any

# MiniMax upstream-facing capability-specific confirm fields.
# These are internal gate-keeping fields that must not be forwarded.
CONTROL_FIELDS: frozenset[str] = frozenset({
    "confirm_asset_source",
    "confirm_quota",
    "confirm_high_cost",
    "confirm_destructive",
    "confirm_long_running",
    "confirm_existing_task",
    "confirm_paid",
    "confirm_very_large_quota",
})


def strip_control_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a new payload dict with all top-level control fields removed.

    Does not modify the input dict.
    """
    if not payload:
        return {}

    return {k: v for k, v in payload.items() if k not in CONTROL_FIELDS}
