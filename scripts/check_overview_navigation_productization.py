#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Overview and navigation productization guard checks."""
import os
import re
import sys


def _base():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _all_overview_files(base):
    """Return all files that make up the Overview page."""
    dirs = [
        os.path.join(base, "frontend/src/pages"),
        os.path.join(base, "frontend/src/components/overview"),
        os.path.join(base, "frontend/src/domain"),
    ]
    files = []
    for d in dirs:
        if os.path.exists(d):
            for root, _, fnames in os.walk(d):
                for f in fnames:
                    if f.endswith(('.ts', '.tsx')):
                        files.append(os.path.join(root, f))
    return files


def _read_all(base):
    """Read all overview-related files into a combined string."""
    files = _all_overview_files(base)
    parts = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                parts.append(fp.read())
        except Exception:
            pass
    return '\n'.join(parts), files


def check_nav_groups(errors, warnings):
    base = _base()
    app_path = os.path.join(base, "frontend/src/App.tsx")
    nav_path = os.path.join(base, "frontend/src/navigation/workbenchNav.ts")
    content = ""
    if os.path.exists(nav_path):
        with open(nav_path, 'r', encoding='utf-8') as f:
            content = f.read()
    elif os.path.exists(app_path):
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        errors.append("[NAV] Neither App.tsx nor workbenchNav.ts found")
        return
    required_groups = ['主工作台', '能力应用', '能力目录', '开发者']
    for g in required_groups:
        if g not in content:
            errors.append(f"[NAV] Navigation group '{g}' not found in nav config")


def check_overview_action_cards(errors, warnings):
    base = _base()
    content, files = _read_all(base)
    if '我想做什么' not in content:
        errors.append("[OVERVIEW] '我想做什么' section not found in any overview component")


def check_overview_diagnostics(errors, warnings):
    base = _base()
    content, files = _read_all(base)
    if '高级诊断' not in content:
        errors.append("[OVERVIEW] '高级诊断' section not found in any overview component")


def check_overview_recent_history(errors, warnings):
    base = _base()
    content, files = _read_all(base)
    if '最近调用' not in content:
        errors.append("[OVERVIEW] '最近调用' section not found in any overview component")


def check_no_renewal_copy(errors, warnings):
    base = _base()
    overview_page = os.path.join(base, "frontend/src/pages/Overview.tsx")
    if not os.path.exists(overview_page):
        errors.append("[OVERVIEW] Overview.tsx not found")
        return
    with open(overview_page, 'r', encoding='utf-8') as f:
        content = f.read()
    bad_patterns = [
        (r"下次续费", "下次续费"),
        (r"年度会员", "年度会员"),
    ]
    for pattern, label in bad_patterns:
        if re.search(pattern, content):
            errors.append(f"[OVERVIEW] Overview.tsx contains hardcoded renewal copy '{label}'")


def check_internal_fields_in_diagnostics(errors, warnings):
    base = _base()
    content, files = _read_all(base)
    bad_fields = [
        'official_current=true',
        'enabled=true',
        'capability_probe=unknown',
        'requires_operation_confirm',
    ]
    has_diagnostics = 'OverviewDiagnostics' in content or '高级诊断' in content
    for field in bad_fields:
        if field in content and not has_diagnostics:
            errors.append(f"[OVERVIEW] '{field}' appears without diagnostics section")


def check_ci_runs_overview_guard(errors, warnings):
    base = _base()
    ci_path = os.path.join(base, ".github/workflows/ci.yml")
    if not os.path.exists(ci_path):
        errors.append("[CI] .github/workflows/ci.yml not found")
        return
    with open(ci_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'check_overview_navigation_productization.py' not in content:
        errors.append("[CI] CI does not run check_overview_navigation_productization.py")


def check_nav_has_developer_section(errors, warnings):
    base = _base()
    app_path = os.path.join(base, "frontend/src/App.tsx")
    nav_path = os.path.join(base, "frontend/src/navigation/workbenchNav.ts")
    content = ""
    for p in [nav_path, app_path]:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
            break
    if 'test-console' not in content:
        errors.append("[NAV] test-console route not found in nav config")
        return
    if '开发者' not in content:
        errors.append("[NAV] '开发者' group not found in nav config")


def main():
    errors = []
    warnings = []
    check_nav_groups(errors, warnings)
    check_overview_action_cards(errors, warnings)
    check_overview_diagnostics(errors, warnings)
    check_overview_recent_history(errors, warnings)
    check_no_renewal_copy(errors, warnings)
    check_internal_fields_in_diagnostics(errors, warnings)
    check_ci_runs_overview_guard(errors, warnings)
    check_nav_has_developer_section(errors, warnings)
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
        print("[PASSED] Overview navigation productization check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
