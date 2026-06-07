#!/usr/bin/env python3
"""验证 capability_runner_templates.json 的结构完整性和与 registry 的一致性。"""
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from backend.app.minimax_core.runner import load_runner_templates, is_runner_supported
from backend.app.minimax_core.registry.loader import get_capability_registry

TEMPLATES_FILE = _root / "backend/app/minimax_core/runner/capability_runner_templates.json"

EXPECTED_CAPABILITIES = {"lyrics-gen", "tts-sync", "voice-list", "image-t2i", "chat-openai", "music-gen", "image-i2i"}
VALID_FIELD_TYPES = {"input", "textarea", "select", "number", "slider", "checkbox"}
VALID_RESULT_TYPES = {"text", "audio", "image", "voice_list", "chat"}
VALID_VALUE_TYPES = {"string", "number", "boolean"}

errors: list[str] = []
warnings: list[str] = []


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        errors.append(f"FAIL: cannot load {path.name}: {e}")
        sys.exit(1)


# ── 1. Load template file ────────────────────────────────────────────────────
templates_data = load_json(TEMPLATES_FILE)

# ── 2. Schema version check ──────────────────────────────────────────────────
if "schema_version" not in templates_data:
    errors.append("missing 'schema_version'")

if "templates" not in templates_data:
    errors.append("missing 'templates'")
    sys.exit(1)

templates = templates_data["templates"]

# ── 2b. Load registry ─────────────────────────────────────────────────────────
reg = get_capability_registry()
all_reg_cap_ids = {cap.id for cap in reg.all()}

# ── 3. Must contain all expected capabilities ─────────────────────────────────
if set(templates.keys()) != EXPECTED_CAPABILITIES:
    missing = EXPECTED_CAPABILITIES - set(templates.keys())
    extra = set(templates.keys()) - EXPECTED_CAPABILITIES
    if missing:
        errors.append(f"missing capabilities: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected capabilities: {sorted(extra)}")

# ── 4. Per-template validation ────────────────────────────────────────────────
REQUIRED_TEMPLATE_FIELDS = [
    "capability_id", "label", "description", "suitable_for",
    "risk_level", "result_type", "form_schema", "payload_template", "next_steps"
]

REQUIRED_FORM_FIELD_FIELDS = ["type", "label", "default"]

for cap_id, template in templates.items():
    if not isinstance(template, dict):
        errors.append(f"'{cap_id}': must be a dict")
        continue

    # 4a. capability_id must equal key
    if template.get("capability_id") != cap_id:
        errors.append(f"'{cap_id}': capability_id '{template.get('capability_id')}' != key '{cap_id}'")

    # 4b. required fields
    for field in REQUIRED_TEMPLATE_FIELDS:
        if field not in template:
            errors.append(f"'{cap_id}': missing field '{field}'")

    # 4c. capability_id must exist in registry (ERROR) AND be runner-supported (ERROR)
    if cap_id not in all_reg_cap_ids:
        errors.append(f"'{cap_id}': capability_id not found in registry")
    if not is_runner_supported(cap_id):
        errors.append(f"'{cap_id}': capability_id not in runner-supported set")

    # 4d. suitable_for must be a list
    if "suitable_for" in template:
        if not isinstance(template["suitable_for"], list):
            errors.append(f"'{cap_id}': 'suitable_for' must be a list")

    # 4e. result_type must be valid
    result_type = template.get("result_type", "")
    if result_type not in VALID_RESULT_TYPES:
        errors.append(f"'{cap_id}': result_type '{result_type}' not in {VALID_RESULT_TYPES}")

    # 4e. form_schema fields validation
    form_schema = template.get("form_schema", {})
    if not isinstance(form_schema, dict):
        errors.append(f"'{cap_id}': 'form_schema' must be a dict")
    else:
        for field_key, field_def in form_schema.items():
            if not isinstance(field_def, dict):
                errors.append(f"'{cap_id}'.form_schema.{field_key}: must be a dict")
                continue

            for req_field in REQUIRED_FORM_FIELD_FIELDS:
                if req_field not in field_def:
                    errors.append(f"'{cap_id}'.form_schema.{field_key}: missing field '{req_field}'")

            field_type = field_def.get("type", "")
            if field_type not in VALID_FIELD_TYPES:
                errors.append(f"'{cap_id}'.form_schema.{field_key}: type '{field_type}' not in {VALID_FIELD_TYPES}")

            # value_type validation
            value_type = field_def.get("value_type", "")
            if value_type and value_type not in VALID_VALUE_TYPES:
                errors.append(f"'{cap_id}'.form_schema.{field_key}: value_type '{value_type}' not in {VALID_VALUE_TYPES}")

            # number / slider must be convertible to number
            if field_type in ("number", "slider"):
                default_str = str(field_def.get("default", ""))
                try:
                    float(default_str)
                except ValueError:
                    errors.append(f"'{cap_id}'.form_schema.{field_key}: default '{default_str}' is not a valid number")

            if field_type == "select":
                opts = field_def.get("options", [])
                if not isinstance(opts, list) or len(opts) == 0:
                    errors.append(f"'{cap_id}'.form_schema.{field_key}: select must have non-empty options")

    # 4f. next_steps validation
    next_steps = template.get("next_steps", [])
    if not isinstance(next_steps, list):
        errors.append(f"'{cap_id}': 'next_steps' must be a list")
    else:
        for i, ns in enumerate(next_steps):
            if not isinstance(ns, dict):
                errors.append(f"'{cap_id}'.next_steps[{i}]: must be a dict")
                continue
            ns_cap_id = ns.get("capability_id", "")
            # Must exist in registry — ERROR if missing
            if ns_cap_id and ns_cap_id not in all_reg_cap_ids:
                errors.append(f"'{cap_id}'.next_steps[{i}]: capability_id '{ns_cap_id}' not found in registry")
            # Warn if exists in registry but not in any known capability set
            if ns_cap_id and ns_cap_id not in EXPECTED_CAPABILITIES:
                warnings.append(f"'{cap_id}'.next_steps[{i}]: capability_id '{ns_cap_id}' not in runner template set (but may be future capability)")
            # blocked must be boolean
            blocked = ns.get("blocked")
            if blocked is not None and not isinstance(blocked, bool):
                errors.append(f"'{cap_id}'.next_steps[{i}]: 'blocked' must be a boolean")
            # guarded must be boolean if present
            guarded = ns.get("guarded")
            if guarded is not None and not isinstance(guarded, bool):
                errors.append(f"'{cap_id}'.next_steps[{i}]: 'guarded' must be a boolean")
            # handoff must be object if present
            handoff = ns.get("handoff")
            if handoff is not None and not isinstance(handoff, dict):
                errors.append(f"'{cap_id}'.next_steps[{i}]: 'handoff' must be an object")
            for ns_field in ["capability_id", "label", "note", "blocked"]:
                if ns_field not in ns:
                    errors.append(f"'{cap_id}'.next_steps[{i}]: missing field '{ns_field}'")

    # 4g. payload_template must be present
    if "payload_template" not in template:
        errors.append(f"'{cap_id}': missing 'payload_template'")

print("Capability Runner Template checks")
print(f"- capabilities: {len(templates)} / {len(EXPECTED_CAPABILITIES)} {'OK' if set(templates.keys()) == EXPECTED_CAPABILITIES else 'FAIL'}")

# ── 5. Output results ─────────────────────────────────────────────────────────
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
