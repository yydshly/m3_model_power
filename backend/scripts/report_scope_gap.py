"""report_scope_gap.py

输出 Token Plan 范围统计：
  - in_scope / warning_only / out_of_scope 各层级能力数量
  - in_scope 中已验收 / 未验收明细（基于实际 probe 结果）
  - 完成率

不读取 .env，不调用真实 API。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.minimax_core.registry.loader import get_capability_registry


def _load_verified_ids() -> set[str]:
    """从已有 probe 结果中加载已验收能力 ID。"""
    verified: set[str] = set()

    # From model_level_probe_report
    mfile = BACKEND / "runtime" / "reports" / "model_level_probe_report.json"
    if mfile.exists():
        with open(mfile, encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("results", []):
            if r.get("probe_status") == "success":
                verified.add(r["capability_id"])

    # From capability_verification (field is 'status', not 'verification_status')
    vfile = BACKEND / "runtime" / "capability_verification" / "latest.json"
    if vfile.exists():
        with open(vfile, encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("results", []):
            if r.get("status") == "success":
                verified.add(r["capability_id"])

    return verified


def main() -> dict:
    caps = get_capability_registry().all()
    verified_ids = _load_verified_ids()

    in_scope = [c for c in caps if c.scope_policy.current_scope == "in_scope"]
    warning = [c for c in caps if c.scope_policy.current_scope == "warning_only"]
    out = [c for c in caps if c.scope_policy.current_scope == "out_of_scope"]

    in_scope_verified_ids = verified_ids & {c.id for c in in_scope}
    in_scope_unverified = [c for c in in_scope if c.id not in verified_ids]

    in_scope_total = len(in_scope)
    in_scope_verified = len(in_scope_verified_ids)
    in_scope_unverified_count = len(in_scope_unverified)
    completion_rate = (in_scope_verified / in_scope_total * 100) if in_scope_total > 0 else 0

    print("=" * 60)
    print("Token Plan 范围统计报告")
    print("=" * 60)
    print(f"in_scope_total:        {in_scope_total}")
    print(f"in_scope_verified:    {in_scope_verified}")
    print(f"in_scope_unverified:  {in_scope_unverified_count}")
    print(f"warning_only_total:   {len(warning)}")
    print(f"out_of_scope_total:   {len(out)}")
    print(f"完成率:               {completion_rate:.1f}% ({in_scope_verified}/{in_scope_total})")
    print()
    print("in_scope_unverified_ids:")
    for c in sorted(in_scope_unverified, key=lambda x: x.id):
        op = c.operation_policy
        reason = "requires_uploaded_asset" if op.requires_uploaded_asset else "no_probe_record"
        print(f"  - {c.id}: {reason}")
    print()
    print("已验收明细（8项）:")
    for cid in sorted(in_scope_verified_ids):
        print(f"  - {cid}")
    print()
    print("warning_only 能力列表:")
    for c in warning:
        print(f"  - {c.id}: {c.scope_policy.scope_reason or 'no reason'}")
    print()
    print("out_of_scope 能力列表:")
    for c in out:
        print(f"  - {c.id}: {c.scope_policy.scope_reason or 'no reason'}")
    print()
    print("=" * 60)

    return {
        "in_scope_total": in_scope_total,
        "in_scope_verified": in_scope_verified,
        "in_scope_unverified": in_scope_unverified_count,
        "warning_only_total": len(warning),
        "out_of_scope_total": len(out),
        "in_scope_unverified_ids": sorted([c.id for c in in_scope_unverified]),
        "completion_rate": completion_rate,
    }


if __name__ == "__main__":
    main()
