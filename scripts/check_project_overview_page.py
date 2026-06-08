#!/usr/bin/env python3
"""Check ProjectOverview page exists, is routed, and has required content."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))

FRONTEND_SRC = _ROOT / "frontend" / "src"


def check_file_exists(path: Path, name: str) -> bool:
    if not path.exists():
        print(f"FAIL: {name} does not exist: {path}")
        return False
    print(f"PASS: {name} exists")
    return True


def main():
    errors = []

    # 1. ProjectOverview.tsx exists
    page_path = FRONTEND_SRC / "pages" / "ProjectOverview.tsx"
    if not check_file_exists(page_path, "ProjectOverview.tsx"):
        errors.append("ProjectOverview.tsx not found")

    # 2. App.tsx registers /project-overview route
    app_path = FRONTEND_SRC / "App.tsx"
    if not check_file_exists(app_path, "App.tsx"):
        errors.append("App.tsx not found")
    else:
        app_content = app_path.read_text(encoding="utf-8")
        if 'path="/project-overview"' not in app_content and 'path="/project-overview"' not in app_content:
            # Try to find any project-overview route
            if "project-overview" not in app_content:
                print("FAIL: App.tsx does not register /project-overview route")
                errors.append("App.tsx missing /project-overview route")
            else:
                print("PASS: App.tsx registers /project-overview route")
        else:
            print("PASS: App.tsx registers /project-overview route")

        if "ProjectOverview" not in app_content:
            print("FAIL: App.tsx does not import ProjectOverview")
            errors.append("App.tsx missing ProjectOverview import")

    # 3. workbenchNav.ts has "项目说明"
    nav_path = FRONTEND_SRC / "navigation" / "workbenchNav.ts"
    if not check_file_exists(nav_path, "workbenchNav.ts"):
        errors.append("workbenchNav.ts not found")
    else:
        nav_content = nav_path.read_text(encoding="utf-8")
        if "项目说明" not in nav_content:
            print("FAIL: workbenchNav.ts does not have '项目说明' nav item")
            errors.append("workbenchNav missing '项目说明' entry")
        else:
            print("PASS: workbenchNav.ts has '项目说明' nav item")

        if "project-overview" not in nav_content:
            print("FAIL: workbenchNav.ts does not link to /project-overview")
            errors.append("workbenchNav missing /project-overview link")

    # 4-12. Page content checks
    if page_path.exists():
        content = page_path.read_text(encoding="utf-8")
        checks = {
            "项目定位": "项目定位",
            "当前已有能力": "当前已有能力",
            "核心架构": "核心架构",
            "技术要点": "技术要点",
            "后续扩展": "后续扩展路线",
            "minimax_core": "minimax_core",
            "RiskGate": "RiskGate",
            "History": "History Store",
            "Diagnostics Trace": "Diagnostics",
        }
        for key, phrase in checks.items():
            if phrase not in content:
                print(f"FAIL: ProjectOverview.tsx missing '{phrase}' content")
                errors.append(f"Page missing: {phrase}")
            else:
                print(f"PASS: ProjectOverview.tsx contains '{phrase}'")

    if errors:
        print(f"\n[FAILED] {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\n[PASSED] Project overview page check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
