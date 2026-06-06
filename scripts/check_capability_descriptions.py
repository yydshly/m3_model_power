#!/usr/bin/env python3
"""验证 capability_descriptions.json 的结构完整性和与 registry 的一致性。"""
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from backend.app.minimax_core.descriptions.loader import load_capability_descriptions
from backend.app.minimax_core.registry.loader import get_capability_registry

REQUIRED_FIELDS = [
    "summary",
    "use_cases",
    "not_recommended_for",
    "input_notes",
    "output_notes",
    "risk_notes",
    "billing_notes",
    "common_errors",
    "product_usage",
    "integration_tips",
]

warnings: list[str] = []
errors: list[str] = []

# ── 1. Load descriptions ───────────────────────────────────────────────
try:
    data = load_capability_descriptions()
except Exception as e:
    print(f"FAIL: cannot load descriptions: {e}")
    sys.exit(1)

# ── 2. Schema version check ──────────────────────────────────────────
if "schema_version" not in data:
    errors.append("missing 'schema_version'")
if "descriptions" not in data:
    errors.append("missing 'descriptions'")
    sys.exit(1)

descriptions = data["descriptions"]

# ── 3. JSON structure checks ──────────────────────────────────────────
for cap_id, desc in descriptions.items():
    if not isinstance(desc, dict):
        errors.append(f"'{cap_id}': must be a dict")
        continue

    for field in REQUIRED_FIELDS:
        if field not in desc:
            errors.append(f"'{cap_id}': missing field '{field}'")

    if "summary" in desc:
        if not isinstance(desc["summary"], str) or not desc["summary"].strip():
            errors.append(f"'{cap_id}': 'summary' must be a non-empty string")

    list_fields = [f for f in REQUIRED_FIELDS if f != "summary"]
    for field in list_fields:
        if field in desc and not isinstance(desc[field], list):
            errors.append(f"'{cap_id}': '{field}' must be a list")

# ── 4. Registry consistency checks ───────────────────────────────────
reg = get_capability_registry()
all_cap_ids = {cap.id for cap in reg.all()}
in_scope_cap_ids = {
    cap.id for cap in reg.all()
    if cap.scope_policy.current_scope == "in_scope" and cap.scope_policy.count_in_completion_rate
}

# 4a. capability_id must exist in registry
for cap_id in descriptions.keys():
    if cap_id not in all_cap_ids:
        warnings.append(f"description for '{cap_id}' but '{cap_id}' not in registry — likely stale entry")

# 4b. check for mismatches between description claims and registry operation_policy
for cap_id, desc in descriptions.items():
    cap_spec = reg.by_id(cap_id)
    if cap_spec is None:
        continue  # already flagged above

    op = cap_spec.operation_policy
    bp = cap_spec.billing_policy

    # confirm_asset_source
    desc_text = json.dumps(desc, ensure_ascii=False).lower()
    mentions_confirm_asset = "confirm_asset_source" in desc_text
    if mentions_confirm_asset and not op.requires_uploaded_asset:
        warnings.append(
            f"'{cap_id}': description mentions 'confirm_asset_source' but "
            f"operation_policy.requires_uploaded_asset = false"
        )
    if not mentions_confirm_asset and op.requires_uploaded_asset:
        warnings.append(
            f"'{cap_id}': operation_policy.requires_uploaded_asset = true "
            f"but description does not mention 'confirm_asset_source'"
        )

    # requires_existing_task
    mentions_existing_task = (
        "requires_existing_task" in desc_text
        or ("task_id" in desc_text and "file_id" in desc_text)
    )
    if mentions_existing_task and not op.requires_existing_task:
        warnings.append(
            f"'{cap_id}': description references task_id/file_id or requires_existing_task "
            f"but operation_policy.requires_existing_task = false"
        )

    # billing / cost warnings
    mentions_cost_confirm = (
        "confirm_quota" in desc_text
        or "billing_notes" in desc.get("billing_notes", [])
        or any("cost" in n.lower() for n in desc.get("risk_notes", []))
    )
    if not mentions_cost_confirm and bp.may_charge_extra:
        warnings.append(
            f"'{cap_id}': billing_policy.may_charge_extra = true "
            f"but billing_notes/risk_notes do not mention cost/confirm"
        )

# ── 5. Coverage stats ────────────────────────────────────────────────
described_ids = set(descriptions.keys())
total = len(all_cap_ids)
in_scope_total = len(in_scope_cap_ids)
described_in_scope = described_ids & in_scope_cap_ids

print(f"Registry total capabilities : {total}")
print(f"Registry in_scope           : {in_scope_total}")
print(f"Description coverage         : {len(described_ids)} / {total}")
print(f"In_scope description coverage: {len(described_in_scope)} / {in_scope_total}")
if in_scope_total > len(described_in_scope):
    missing = sorted(in_scope_cap_ids - described_ids)
    print(f"Missing in_scope            : {missing}")

# ── 6. Emit errors/warnings ──────────────────────────────────────────
if warnings:
    print(f"\n{len(warnings)} WARNING(S):")
    for w in warnings:
        print(f"  ! {w}")

if errors:
    print(f"\n{len(errors)} ERROR(S):")
    for e in errors:
        print(f"  X {e}")
    sys.exit(1)

print("\nAll checks PASSED")
