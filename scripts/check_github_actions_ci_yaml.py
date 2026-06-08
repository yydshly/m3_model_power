#!/usr/bin/env python3
"""检查 GitHub Actions CI YAML 文件的语法完整性和 guard 覆盖度。"""
import sys
import yaml
from pathlib import Path


REQUIRED_GUARD_SCRIPTS = [
    "scripts/check_github_actions_ci_yaml.py",
    "scripts/check_official_docs_full_drift.py",
    "scripts/check_capability_source_matrix_coverage.py",
    "scripts/check_model_quota_and_protocol_ui_consistency.py",
    "scripts/check_registry_fact_consistency.py",
    "scripts/check_quota_sensitive_confirmation_ui.py",
    "scripts/check_workbench_model_status_copy.py",
    "scripts/check_capability_profile_model_alignment.py",
    "scripts/check_frontend_copy_no_leaky_internal_terms.py",
    "scripts/check_shared_confirmation_logic.py",
    "scripts/check_chatpanel_model_selection_sync.py",
    "scripts/check_invocation_history_and_assets.py",
    "scripts/check_productized_test_console.py",
    "scripts/check_overview_navigation_productization.py",
    "scripts/check_productized_workbench_docs.py",
    "scripts/check_frontend_api_proxy.py",
    "scripts/check_demo_payload_coverage.py",
    "scripts/check_history_write_read.py",
    "scripts/check_invoke_history_integration.py",
    "scripts/check_payload_validation_and_model_sync.py",
    "scripts/check_history_observability.py",
    "scripts/check_runtime_smoke.py",
    "scripts/check_interaction_regression.py",
    "scripts/check_special_panels_history.py",
    "scripts/check_history_result_summary.py",
    "scripts/check_project_overview_page.py",
    "scripts/check_startup_contract.py",
]

REQUIRED_CI_TERMS = [
    "pip install -e backend",
    "npm ci",
    "npm run build",
    "python -m compileall backend scripts",
]


def main():
    errors = []

    path = Path(".github/workflows/ci.yml")
    if not path.exists():
        errors.append(".github/workflows/ci.yml not found")
        print("[FAILED]")
        for err in errors:
            print(f"  - {err}")
        return 1

    content = path.read_text(encoding="utf-8")

    # Check for common YAML syntax errors
    if "run |" in content:
        errors.append("Invalid GitHub Actions syntax: 'run |' should be 'run: |'")

    try:
        data = yaml.safe_load(content)
        if data is None:
            errors.append("YAML parsed as null — empty or invalid file")
        elif not isinstance(data, dict):
            errors.append(f"YAML root must be a mapping, got {type(data).__name__}")
    except yaml.YAMLError as exc:
        errors.append(f"YAML parse failed: {exc}")

    # Check required high-level CI terms
    required_terms = [
        "pull_request",
        "push",
        "Run guard scripts",
        "Compile Python",
        "Typecheck and build",
    ]
    for term in required_terms:
        if term not in content:
            errors.append(f"Missing required term: '{term}'")

    # Check every required guard script is run in CI
    for script in REQUIRED_GUARD_SCRIPTS:
        if script not in content:
            errors.append(f"CI does not run required guard script: {script}")

    # Check required dependency installation and build commands
    for term in REQUIRED_CI_TERMS:
        if term not in content:
            errors.append(f"Missing CI command: {term}")

    if errors:
        print(f"[FAILED] {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[PASSED] GitHub Actions CI YAML is valid and all required guards are covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
