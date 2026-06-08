#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interaction regression guard: static checks for page navigation and history refresh.

Checks:
1. CapabilityWorkflows.tsx must contain /capability-runner?capability=
2. CapabilityWorkflows.tsx must contain /test-console?capability=
3. CapabilityScenarios.tsx must contain /capability-runner?capability=
4. CapabilityScenarios.tsx must contain getWorkflowLink
5. CapabilityRunner.tsx must display from_workflow / from_scenario source
6. CapabilityRunner.tsx must call getCapabilityHistory
7. CapabilityRunner.tsx backend calls must trigger history refresh (uses onDone pattern)
8. TestConsole.tsx must refresh history after invoke/risk-check
9. Capability.tsx must not contain "支持 8 个模型调用" hardcoded copy
10. CapabilityRunner.tsx extractImageUrl must not unconditionally return file_url/download_url
"""
import os
import re
import sys


def _base():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def check_workflows_runner_links(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/CapabilityWorkflows.tsx")
    if not os.path.exists(path):
        errors.append(f"[WORKFLOWS] {path} not found")
        return
    content = _read(path)

    if '/capability-runner?capability=' not in content:
        errors.append("[WORKFLOWS] /capability-runner?capability= link not found")

    if '/test-console?capability=' not in content:
        errors.append("[WORKFLOWS] /test-console?capability= link not found")

    # Check that list-level "体验" link includes from_workflow
    # Pattern: /capability-runner?capability=${}&from_workflow=
    if not re.search(r'capability-runner\?capability=.*?\&from_workflow=', content):
        errors.append("[WORKFLOWS] workflow list '体验' link missing from_workflow param")


def check_scenarios_runner_links(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/CapabilityScenarios.tsx")
    if not os.path.exists(path):
        errors.append(f"[SCENARIOS] {path} not found")
        return
    content = _read(path)

    if '/capability-runner?capability=' not in content:
        errors.append("[SCENARIOS] /capability-runner?capability= link not found")

    if 'getWorkflowLink' not in content:
        errors.append("[SCENARIOS] getWorkflowLink not found in CapabilityScenarios.tsx")

    # Check that scenario capability tags include from_scenario
    if not re.search(r'capability-runner\?capability=.*?\&from_scenario=', content):
        errors.append("[SCENARIOS] scenario capability link missing from_scenario param")


def check_runner_shows_source(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/CapabilityRunner.tsx")
    if not os.path.exists(path):
        errors.append(f"[RUNNER] {path} not found")
        return
    content = _read(path)

    if 'from_workflow' not in content and 'fromScenario' not in content:
        errors.append("[RUNNER] CapabilityRunner.tsx does not read from_workflow or fromScenario query param")


def check_runner_calls_history(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/CapabilityRunner.tsx")
    content = _read(path)

    if 'getCapabilityHistory' not in content:
        errors.append("[RUNNER] CapabilityRunner.tsx does not call getCapabilityHistory")


def check_runner_refreshes_history_on_done(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/CapabilityRunner.tsx")
    content = _read(path)

    # Check that handleRun or the main execution path calls onDone
    # The onDone prop is passed from CapabilityRunnerLoaded and calls refreshHistory
    if 'onDone' not in content:
        errors.append("[RUNNER] CapabilityRunner.tsx does not use onDone callback for history refresh")


def check_runner_history_fallback(errors, warnings):
    """CapabilityRunner must have a fallback to getTestConsoleHistory when
    getCapabilityHistory fails, so the runner never shows a hard 404 to users."""
    base = _base()
    path = os.path.join(base, "frontend/src/pages/CapabilityRunner.tsx")
    content = _read(path)

    if 'getTestConsoleHistory' not in content:
        errors.append("[RUNNER] CapabilityRunner.tsx does not import getTestConsoleHistory for fallback")

    # Must have fallback logic when getCapabilityHistory fails
    if '.catch' not in content or 'getTestConsoleHistory' not in content:
        errors.append("[RUNNER] CapabilityRunner.tsx refreshHistory does not fall back to getTestConsoleHistory on getCapabilityHistory failure")

    if 'historyFallbackUsed' not in content:
        errors.append("[RUNNER] CapabilityRunner.tsx does not track historyFallbackUsed state")

    # UI must show a notice when fallback is used
    if '当前能力历史接口不可用' not in content and 'historyFallbackUsed' not in content:
        warnings.append("[RUNNER] CapabilityRunner.tsx may not show a user-visible notice when fallback is triggered")


def check_api_capability_history_error_message(errors, warnings):
    """api.ts getCapabilityHistory must provide a descriptive error message."""
    base = _base()
    path = os.path.join(base, "frontend/src/api.ts")
    if not os.path.exists(path):
        errors.append(f"[API] {path} not found")
        return
    content = _read(path)

    # Must not show cryptic "capability history 404"
    if re.search(r'throw.*Error\(\s*`capability history \$\{r\.status\}', content):
        errors.append("[API] api.ts getCapabilityHistory still uses cryptic 'capability history 404' error message")


def check_testconsole_refreshes_history(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/TestConsole.tsx")
    if not os.path.exists(path):
        errors.append(f"[TESTCONSOLE] {path} not found")
        return
    content = _read(path)

    if 'refreshHistory' not in content:
        errors.append("[TESTCONSOLE] TestConsole.tsx does not call refreshHistory")

    # Check that RiskCheckPanel and InvokePanel call onDone after API calls
    # The onDone prop of those panels should be refreshHistory
    if 'onDone={refreshHistory}' not in content and 'onDone={ onDone }' not in content:
        errors.append("[TESTCONSOLE] TestConsole.tsx panels do not pass refreshHistory as onDone")


def check_capability_no_hardcoded_8_models(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/Capability.tsx")
    if not os.path.exists(path):
        errors.append(f"[CAPABILITY] {path} not found")
        return
    content = _read(path)

    if re.search(r'支持\s*\d+\s*个模型', content):
        errors.append("[CAPABILITY] Capability.tsx contains hardcoded '支持 X 个模型' copy that conflicts with displayed list")


def check_runner_file_url_not_unconditional(errors, warnings):
    base = _base()
    path = os.path.join(base, "frontend/src/pages/CapabilityRunner.tsx")
    if not os.path.exists(path):
        return
    content = _read(path)

    # extractImageUrl should not unconditionally return file_url or download_url
    # The old buggy pattern: `if (typeof d.file_url === 'string' && d.file_url) return d.file_url`
    # without an image-extension check
    bad_patterns = [
        (
            r"d\.file_url\s*===\s*['\"]string['\"].*?return\s+d\.file_url(?!\s)",
            "file_url unconditional return without image check"
        ),
        (
            r"d\.download_url\s*===\s*['\"]string['\"].*?return\s+d\.download_url(?!\s)",
            "download_url unconditional return without image check"
        ),
    ]

    for pattern, label in bad_patterns:
        if re.search(pattern, content, re.DOTALL):
            errors.append(f"[RUNNER] CapabilityRunner.tsx extractImageUrl contains: {label}")


def check_ci_includes_smoke_guard(errors, warnings):
    base = _base()
    ci_path = os.path.join(base, ".github/workflows/ci.yml")
    if not os.path.exists(ci_path):
        errors.append("[CI] .github/workflows/ci.yml not found")
        return
    content = _read(ci_path)
    if 'check_runtime_smoke.py' not in content:
        errors.append("[CI] CI does not run check_runtime_smoke.py")
    if 'check_interaction_regression.py' not in content:
        errors.append("[CI] CI does not run check_interaction_regression.py")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    check_workflows_runner_links(errors, warnings)
    check_scenarios_runner_links(errors, warnings)
    check_runner_shows_source(errors, warnings)
    check_runner_calls_history(errors, warnings)
    check_runner_refreshes_history_on_done(errors, warnings)
    check_runner_history_fallback(errors, warnings)
    check_testconsole_refreshes_history(errors, warnings)
    check_capability_no_hardcoded_8_models(errors, warnings)
    check_runner_file_url_not_unconditional(errors, warnings)
    check_api_capability_history_error_message(errors, warnings)
    check_ci_includes_smoke_guard(errors, warnings)

    if errors:
        print(f"[FAILED] {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 1
    else:
        print("[PASSED] Interaction regression check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
