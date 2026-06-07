#!/usr/bin/env python3
"""
Check script for Official Docs P0 Alignment Fix

Validates that P0 issues identified in OFFICIAL_DOCS_ALIGNMENT_AUDIT.md
have been resolved:
 1. MiniMax-M3 protocols contains openai/anthropic/responses
 2. MiniMax-M2.7 protocols contains openai/anthropic
 3. MiniMax-M2.7-highspeed protocols contains openai/anthropic
 4. MiniMax-M2.5 protocols contains openai/anthropic
 5. MiniMax-M2.5-highspeed protocols contains openai/anthropic
 6. MiniMax-M2.1 protocols contains openai/anthropic
 7. MiniMax-M2.1-highspeed protocols contains openai/anthropic
 8. MiniMax-M2 protocols contains openai/anthropic
 9. chat-anthropic Runner model options count == 8
10. chat-openai Runner model options count == 8
11. chat-anthropic note mentions M3 multimodal / M2.x text boundary
12. chat-openai note mentions smoke表单
13. OFFICIAL_DOCS_ALIGNMENT_AUDIT.md has P0 fix record

No real MiniMax API calls are made.
"""

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
MODELS_YAML_PATH = REPO_ROOT / "backend" / "config" / "models.yaml"
TEMPLATES_JSON_PATH = REPO_ROOT / "backend" / "app" / "minimax_core" / "runner" / "capability_runner_templates.json"
AUDIT_DOC_PATH = REPO_ROOT / "docs" / "OFFICIAL_DOCS_ALIGNMENT_AUDIT.md"


class CheckResult:
    def __init__(self):
        self.checks: list[dict[str, Any]] = []

    def pass_(self, name: str, detail: str = ""):
        self.checks.append({"name": name, "status": "PASS", "detail": detail})

    def fail(self, name: str, detail: str = ""):
        self.checks.append({"name": name, "status": "FAIL", "detail": detail})

    def summary(self) -> dict[str, Any]:
        passed = sum(1 for c in self.checks if c["status"] == "PASS")
        failed = sum(1 for c in self.checks if c["status"] == "FAIL")
        return {
            "total": len(self.checks),
            "passed": passed,
            "failed": failed,
            "all_passed": failed == 0,
        }

    def print_report(self):
        print("=" * 70)
        print("Official Docs P0 Alignment Fix — Validation Report")
        print("=" * 70)
        for check in self.checks:
            status_tag = {"PASS": "[PASS]", "FAIL": "[FAIL]"}[check["status"]]
            print(f"{status_tag} {check['name']}")
            if check["detail"]:
                print(f"       {check['detail']}")

        s = self.summary()
        print(f"\n{'='*70}")
        print(f"Total: {s['total']} | Passed: {s['passed']} | Failed: {s['failed']}")
        if s["all_passed"]:
            print("RESULT: ALL PASSED")
        else:
            print("RESULT: FAILED")
        return s["all_passed"]


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_checks() -> bool:
    result = CheckResult()

    # Load data
    models_data = load_yaml(MODELS_YAML_PATH)
    templates_data = load_json(TEMPLATES_JSON_PATH)
    audit_content = AUDIT_DOC_PATH.read_text(encoding="utf-8") if AUDIT_DOC_PATH.exists() else ""

    models: list[dict[str, Any]] = models_data.get("models", [])
    model_by_id = {m["id"]: m for m in models}
    templates: dict[str, Any] = templates_data.get("templates", {})

    # ── Protocol checks ──────────────────────────────────────────────────────

    protocol_checks = [
        # (model_id, expected_protocols_set)
        ("MiniMax-M3",          {"openai", "anthropic", "responses"}),
        ("MiniMax-M2.7",        {"openai", "anthropic"}),
        ("MiniMax-M2.7-highspeed", {"openai", "anthropic"}),
        ("MiniMax-M2.5",        {"openai", "anthropic"}),
        ("MiniMax-M2.5-highspeed", {"openai", "anthropic"}),
        ("MiniMax-M2.1",        {"openai", "anthropic"}),
        ("MiniMax-M2.1-highspeed", {"openai", "anthropic"}),
        ("MiniMax-M2",          {"openai", "anthropic"}),
    ]

    for model_id, expected in protocol_checks:
        if model_id not in model_by_id:
            result.fail(f"protocols[{model_id}]", f"Model {model_id} not found in models.yaml")
            continue
        actual = set(model_by_id[model_id].get("protocols", []))
        missing = expected - actual
        extra = actual - expected
        if missing or extra:
            result.fail(
                f"protocols[{model_id}]",
                f"Expected {sorted(expected)}, got {sorted(actual)}",
            )
        else:
            result.pass_(f"protocols[{model_id}]", f"{sorted(actual)}")

    # ── Runner dropdown checks ──────────────────────────────────────────────

    for cap_id in ("chat-anthropic", "chat-openai"):
        template = templates.get(cap_id, {})
        form_schema = template.get("form_schema", {})
        model_field = form_schema.get("model", {})
        options = model_field.get("options", [])
        note = model_field.get("note", "")

        # Check option count
        if len(options) == 8:
            result.pass_(f"{cap_id} model count", f"8 models in dropdown")
        else:
            result.fail(
                f"{cap_id} model count",
                f"Expected 8, got {len(options)}",
            )

        # Check M3 present
        m3_values = [o["value"] for o in options if o["value"] == "MiniMax-M3"]
        if m3_values:
            result.pass_(f"{cap_id} has MiniMax-M3", "")
        else:
            result.fail(f"{cap_id} has MiniMax-M3", "MiniMax-M3 not in dropdown")

        # Check all 8 expected models present
        expected_models = {
            "MiniMax-M3", "MiniMax-M2.7-highspeed", "MiniMax-M2.7",
            "MiniMax-M2.5-highspeed", "MiniMax-M2.5",
            "MiniMax-M2.1-highspeed", "MiniMax-M2.1", "MiniMax-M2",
        }
        actual_values = {o["value"] for o in options}
        missing_models = expected_models - actual_values
        if not missing_models:
            result.pass_(f"{cap_id} all 8 models present", "")
        else:
            result.fail(f"{cap_id} all 8 models present", f"Missing: {sorted(missing_models)}")

        # Check note content
        if cap_id == "chat-anthropic":
            if "M3" in note and ("多模态" in note or "图片" in note or "视频" in note) and "M2" in note:
                result.pass_(f"{cap_id} note mentions multimodal boundary", "")
            else:
                result.fail(
                    f"{cap_id} note mentions multimodal boundary",
                    f"Note does not clearly mention M3 multimodal and M2.x text boundary",
                )
        elif cap_id == "chat-openai":
            if "smoke" in note.lower() or "文本" in note:
                result.pass_(f"{cap_id} note mentions smoke表单", "")
            else:
                result.fail(
                    f"{cap_id} note mentions smoke表单",
                    f"Note does not mention current Runner is smoke表单",
                )

    # ── Audit doc P0 fix record ─────────────────────────────────────────────

    p0_keywords = ["P0", "修复", "resolved", "fixed", "p0"]
    has_p0_record = any(kw in audit_content for kw in p0_keywords)
    if has_p0_record:
        result.pass_("Audit doc has P0 fix record", "")
    else:
        result.fail("Audit doc has P0 fix record", "No P0 fix record found in audit doc")

    return result.print_report()


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
