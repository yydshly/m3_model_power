"""Verification summary and index API.

GET /api/verification/summary
  → {in_scope_total, in_scope_verified, in_scope_unverified, in_scope_unverified_ids, completion_rate}

GET /api/verification/index
  → Full MINIMAX_CAPABILITY_VERIFICATION_INDEX.json contents
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/verification", tags=["verification"])

# Path to committed aggregate index
_INDEX_PATH = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "MINIMAX_CAPABILITY_VERIFICATION_INDEX.json"


def _load_index() -> dict:
    if not _INDEX_PATH.exists():
        raise HTTPException(503, "verification index not available")
    return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))


@router.get("/summary")
async def summary() -> dict:
    """Return scope-gap summary counts from the aggregate verification index."""
    idx = _load_index()
    caps = idx.get("capabilities", {})

    # Also load capability specs to get scope_policy for each cap
    from ..minimax_core.registry.loader import get_capability_registry

    cap_reg = get_capability_registry()

    in_scope_total = 0
    in_scope_verified = 0
    in_scope_unverified = 0
    in_scope_unverified_ids: list[str] = []

    for cap_id, record in caps.items():
        cap_spec = cap_reg.by_id(cap_id)
        if cap_spec is None:
            continue
        sp = cap_spec.scope_policy
        if not sp.count_in_completion_rate:
            continue
        if sp.current_scope == "in_scope":
            in_scope_total += 1
            if record.get("verified"):
                in_scope_verified += 1
            else:
                in_scope_unverified += 1
                in_scope_unverified_ids.append(cap_id)

    total = in_scope_total
    completion_rate = (in_scope_verified / total * 100) if total > 0 else 0.0

    return {
        "in_scope_total": in_scope_total,
        "in_scope_verified": in_scope_verified,
        "in_scope_unverified": in_scope_unverified,
        "in_scope_unverified_ids": in_scope_unverified_ids,
        "completion_rate": round(completion_rate, 1),
    }


@router.get("/index")
async def index() -> dict:
    """Return the full committed aggregate verification index."""
    return _load_index()
