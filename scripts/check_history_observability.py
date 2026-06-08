"""
Guard: check_history_observability.py

Checks:
1. InvocationHistoryPanel supports showCapabilityHeader
2. TestConsole uses showCapabilityHeader={true}
3. OverviewRecentHistory shows capability_id
4. InvokePanel shows history_id banner
5. InvokePanel onDone accepts { history_id, capability_id }
6. Capability.tsx shows capability_id filter in history empty state
7. Capability.tsx has "查看全部历史" link
8. CapabilityRunner history section has "查看全部历史" link
9. history-smoke-test is marked as "测试记录" in InvocationHistoryPanel
"""
import re
import sys
from pathlib import Path

FRONTEND = Path("frontend/src")


def check_ihp_show_capability_header():
    """1. InvocationHistoryPanel supports showCapabilityHeader"""
    f = FRONTEND / "components" / "InvocationHistoryPanel.tsx"
    if not f.exists():
        return False, "InvocationHistoryPanel.tsx not found"
    content = f.read_text(encoding="utf-8")
    if "showCapabilityHeader" not in content:
        return False, "showCapabilityHeader not found in InvocationHistoryPanel"
    return True, "InvocationHistoryPanel supports showCapabilityHeader"


def check_test_console_shows_capability_id():
    """2. TestConsole uses showCapabilityHeader={true}"""
    f = FRONTEND / "pages" / "TestConsole.tsx"
    if not f.exists():
        return False, "TestConsole.tsx not found"
    content = f.read_text(encoding="utf-8")
    if "showCapabilityHeader" not in content:
        return False, "TestConsole does not pass showCapabilityHeader to InvocationHistoryPanel"
    # Accept both shorthand (showCapabilityHeader) and explicit (showCapabilityHeader={true})
    shorthand = bool(re.search(r"showCapabilityHeader\b(?!\s*=)", content))
    explicit = "showCapabilityHeader={true}" in content or "showCapabilityHeader={ true }" in content
    if not (shorthand or explicit):
        return False, "TestConsole does not set showCapabilityHeader={true}"
    return True, "TestConsole uses showCapabilityHeader={true}"


def check_overview_recent_history_shows_capability_id():
    """3. OverviewRecentHistory shows capability_id"""
    f = FRONTEND / "components" / "overview" / "OverviewRecentHistory.tsx"
    if not f.exists():
        return False, "OverviewRecentHistory.tsx not found"
    content = f.read_text(encoding="utf-8")
    if "capability_id" not in content:
        return False, "OverviewRecentHistory does not display capability_id"
    return True, "OverviewRecentHistory shows capability_id"


def check_invoke_panel_history_id():
    """4. InvokePanel shows history_id banner"""
    f = FRONTEND / "components" / "InvokePanel.tsx"
    if not f.exists():
        return False, "InvokePanel.tsx not found"
    content = f.read_text(encoding="utf-8")
    if "lastHistoryId" not in content:
        return False, "InvokePanel does not track lastHistoryId"
    if "历史已写入" not in content and "history_id" not in content.lower():
        return False, "InvokePanel does not show history_id banner"
    return True, "InvokePanel shows history_id banner"


def check_invoke_panel_ondone_signature():
    """5. InvokePanel onDone accepts { history_id, capability_id }"""
    f = FRONTEND / "components" / "InvokePanel.tsx"
    if not f.exists():
        return False, "InvokePanel.tsx not found"
    content = f.read_text(encoding="utf-8")
    # onDone should accept optional info with history_id and capability_id
    if "onDone?: (info?: { history_id" not in content:
        return False, "InvokePanel onDone does not accept { history_id, capability_id }"
    return True, "InvokePanel onDone accepts { history_id, capability_id }"


def check_capability_history_filter_diagnostic():
    """6. Capability.tsx shows capability_id filter in history empty state"""
    f = FRONTEND / "pages" / "Capability.tsx"
    if not f.exists():
        return False, "Capability.tsx not found"
    content = f.read_text(encoding="utf-8")
    issues = []
    if "capability_id = " not in content and "capability_id=" not in content:
        issues.append("Capability.tsx does not show capability_id in filter diagnostic")
    if "全局最近有" not in content:
        issues.append("Capability.tsx does not show global history diagnostic")
    if issues:
        return False, "; ".join(issues)
    return True, "Capability.tsx shows capability_id filter diagnostic"


def check_capability_view_all_history():
    """7. Capability.tsx has View all history link"""
    f = FRONTEND / "pages" / "Capability.tsx"
    if not f.exists():
        return False, "Capability.tsx not found"
    content = f.read_text(encoding="utf-8")
    if "查看全部历史" not in content:
        return False, "Capability.tsx does not have '查看全部历史' link"
    return True, "Capability.tsx has '查看全部历史' link"


def check_runner_view_all_history():
    """8. CapabilityRunner has View all history link"""
    f = FRONTEND / "pages" / "CapabilityRunner.tsx"
    if not f.exists():
        return False, "CapabilityRunner.tsx not found"
    content = f.read_text(encoding="utf-8")
    if "查看全部历史" not in content:
        return False, "CapabilityRunner does not have '查看全部历史' link"
    return True, "CapabilityRunner has '查看全部历史' link"


def check_history_smoke_test_marker():
    """9. history-smoke-test marked as '测试记录' in InvocationHistoryPanel"""
    f = FRONTEND / "components" / "InvocationHistoryPanel.tsx"
    if not f.exists():
        return False, "InvocationHistoryPanel.tsx not found"
    content = f.read_text(encoding="utf-8")
    if "history-smoke-test" not in content:
        return False, "InvocationHistoryPanel does not check for history-smoke-test"
    if "测试记录" not in content:
        return False, "InvocationHistoryPanel does not mark history-smoke-test as '测试记录'"
    return True, "history-smoke-test marked as '测试记录'"


def main():
    checks = [
        ("InvocationHistoryPanel showCapabilityHeader", check_ihp_show_capability_header),
        ("TestConsole showCapabilityHeader={true}", check_test_console_shows_capability_id),
        ("OverviewRecentHistory shows capability_id", check_overview_recent_history_shows_capability_id),
        ("InvokePanel history_id banner", check_invoke_panel_history_id),
        ("InvokePanel onDone signature", check_invoke_panel_ondone_signature),
        ("Capability.tsx history diagnostic", check_capability_history_filter_diagnostic),
        ("Capability.tsx View all history link", check_capability_view_all_history),
        ("CapabilityRunner View all history link", check_runner_view_all_history),
        ("history-smoke-test marker", check_history_smoke_test_marker),
    ]

    all_passed = True
    for name, check_fn in checks:
        ok, msg = check_fn()
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {msg}")
        if not ok:
            all_passed = False

    if all_passed:
        print("\nAll checks PASSED.")
        sys.exit(0)
    else:
        print("\nSome checks FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
