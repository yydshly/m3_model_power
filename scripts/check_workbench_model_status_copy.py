#!/usr/bin/env python3
"""
Check script for Workbench Model Status Copy fixes.

Validates that P0 copy/semantic issues in Overview.tsx, StatusBadge.tsx,
Capability.tsx, and App.tsx have been resolved:
 1. Overview.tsx no longer contains banned phrases
 2. Overview.tsx contains required semantic labels
 3. StatusBadge.tsx no longer contains banned phrases
 4. StatusBadge.tsx contains required billing labels
 5. Capability.tsx contains required model selection explanation
 6. App.tsx footer contains "能力配置" and "启用模型"

No real MiniMax API calls are made.
"""

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
OVERVIEW_PATH = REPO_ROOT / "frontend" / "src" / "pages" / "Overview.tsx"
STATUS_BADGE_PATH = REPO_ROOT / "frontend" / "src" / "components" / "StatusBadge.tsx"
CAPABILITY_PATH = REPO_ROOT / "frontend" / "src" / "pages" / "Capability.tsx"
APP_PATH = REPO_ROOT / "frontend" / "src" / "App.tsx"


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
        print("Workbench Model Status Copy — Validation Report")
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


def run_checks() -> bool:
    result = CheckResult()

    overview = OVERVIEW_PATH.read_text(encoding="utf-8") if OVERVIEW_PATH.exists() else ""
    status_badge = STATUS_BADGE_PATH.read_text(encoding="utf-8") if STATUS_BADGE_PATH.exists() else ""
    capability = CAPABILITY_PATH.read_text(encoding="utf-8") if CAPABILITY_PATH.exists() else ""
    app = APP_PATH.read_text(encoding="utf-8") if APP_PATH.exists() else ""

    # ── 1. Overview.tsx banned phrases ────────────────────────────────────────
    banned_overview = [
        "支持 MiniMax 全系模型",
        "月度约 12 亿",
        "实际可用",
        "未 live 验收",
    ]
    for phrase in banned_overview:
        if phrase in overview:
            result.fail(f"Overview banned phrase: {phrase!r}", f"Found in Overview.tsx")
        else:
            result.pass_(f"Overview banned phrase: {phrase!r}", "Not found")

    # ── 2. Overview.tsx required labels ────────────────────────────────────────
    required_overview_labels = [
        "Chat live 可用",
        "前端启用模型",
        "全量配置模型",
        "capability_probe 待探测",
        "历史/废弃模型",
        "以下信息基于本项目",
        "backend/config",
    ]
    for label in required_overview_labels:
        if label in overview:
            result.pass_(f"Overview required label: {label!r}", "Found")
        else:
            result.fail(f"Overview required label: {label!r}", "Not found in Overview.tsx")

    # ── 3. StatusBadge.tsx banned phrases ─────────────────────────────────────
    if "另计费" in status_badge:
        result.fail("StatusBadge banned phrase: '另计费'", "Found in StatusBadge.tsx")
    else:
        result.pass_("StatusBadge banned phrase: '另计费'", "Not found")

    # ── 4. StatusBadge.tsx required labels ────────────────────────────────────
    required_status_labels = ["极速额度", "标准计量", "不等于一定产生额外收费"]
    for label in required_status_labels:
        if label in status_badge:
            result.pass_(f"StatusBadge required label: {label!r}", "Found")
        else:
            result.fail(f"StatusBadge required label: {label!r}", "Not found in StatusBadge.tsx")

    # ── 5. Capability.tsx model selection explanation ──────────────────────────
    capability_required = [
        "默认选择优先成本友好模型",
        "不代表官方推荐模型",
    ]
    for phrase in capability_required:
        if phrase in capability:
            result.pass_(f"Capability required phrase: {phrase!r}", "Found")
        else:
            result.fail(f"Capability required phrase: {phrase!r}", "Not found in Capability.tsx")

    # ── 6. App.tsx footer ─────────────────────────────────────────────────────
    if "能力配置" in app and "启用模型" in app:
        result.pass_("App.tsx footer: '能力配置' and '启用模型'", "Both found")
    else:
        result.fail("App.tsx footer: '能力配置' and '启用模型'", "Missing in App.tsx")

    return result.print_report()


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
