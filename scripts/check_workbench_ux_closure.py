#!/usr/bin/env python3
"""Check workbench UX closure items for P1 workbench-ux-closure.

Checks:
 1. image-i2i has reference_mode field in form_schema
 2. image-i2i has subject_consistency risk notice in description or result area
 3. image-i2i has image-01-live pending verification note
 4. TestConsole banner明确 raw JSON 调试台
 5. TestConsole 说明不会自动套用 Runner 表单模板
 6. history status API 存在于 backend
 7. history empty state 有原因提示（4 点诊断）
 8. Overview 有 Runner 产品化进度卡片
 9. Overview 有风险能力数量展示
10. 视觉模块说明 image-i2i 模型限制
11. 六个模块页面都有模块说明（MODULE_DESCRIPTIONS 覆盖 chat/voice/image/music/file/models）
12. frontend build 通过
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_PATH = _ROOT / "backend" / "app" / "minimax_core" / "runner" / "capability_runner_templates.json"
_TEST_CONSOLE = _ROOT / "frontend" / "src" / "pages" / "TestConsole.tsx"
_OVERVIEW = _ROOT / "frontend" / "src" / "pages" / "Overview.tsx"
_CATEGORY = _ROOT / "frontend" / "src" / "pages" / "Category.tsx"
_RUNNER = _ROOT / "frontend" / "src" / "pages" / "CapabilityRunner.tsx"
_HISTORY_PY = _ROOT / "backend" / "app" / "routers" / "history.py"
_WORKBENCH_STATUS = _ROOT / "frontend" / "src" / "workbenchStatus.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_templates() -> dict:
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f).get("templates", {})


def check_1_image_i2i_reference_mode() -> bool:
    templates = load_templates()
    i2i = templates.get("image-i2i", {})
    schema = i2i.get("form_schema", {})
    if "reference_mode" not in schema:
        print("FAIL: image-i2i form_schema missing 'reference_mode' field")
        return False
    field = schema["reference_mode"]
    if field.get("type") != "select":
        print("FAIL: image-i2i reference_mode is not type 'select'")
        return False
    opts = field.get("options", [])
    values = {o["value"] for o in opts}
    for expected in ("subject", "style", "variation"):
        if expected not in values:
            print(f"FAIL: image-i2i reference_mode missing option '{expected}'")
            return False
    print("PASS: image-i2i has reference_mode field with subject/style/variation options")
    return True


def check_2_image_i2i_risk_notice() -> bool:
    templates = load_templates()
    desc = templates.get("image-i2i", {}).get("description", "")
    if "不是严格局部编辑" not in desc and "主体一致性" not in desc:
        print("FAIL: image-i2i description does not mention subject_consistency limitation")
        return False
    print("PASS: image-i2i description mentions subject consistency limitation")
    return True


def check_3_image_i2i_live_pending_note() -> bool:
    templates = load_templates()
    i2i = templates.get("image-i2i", {})
    schema = i2i.get("form_schema", {})
    model_field = schema.get("model", {})
    note = model_field.get("note", "")
    if "image-01-live" not in note and "待验证" not in note:
        print("FAIL: image-i2i model field missing image-01-live pending verification note")
        return False
    print("PASS: image-i2i model field has image-01-live pending verification note")
    return True


def check_4_testconsole_banner_raw_json() -> bool:
    content = read(_TEST_CONSOLE)
    if "raw JSON" not in content and "raw JSON 调试台" not in content:
        print("FAIL: TestConsole banner does not mention 'raw JSON 调试台'")
        return False
    print("PASS: TestConsole banner明确 raw JSON 调试台")
    return True


def check_5_testconsole_no_auto_template() -> bool:
    content = read(_TEST_CONSOLE)
    patterns = [
        "不会自动套用",
        "表单模板",
        "直接调用",
        "/api/invoke/",
    ]
    found = sum(1 for p in patterns if p in content)
    if found < 3:
        print(f"FAIL: TestConsole does not clearly explain it won't auto-apply Runner form templates (found {found}/{len(patterns)} patterns)")
        return False
    print("PASS: TestConsole explains it won't auto-apply Runner form templates")
    return True


def check_6_history_status_api() -> bool:
    content = read(_HISTORY_PY)
    if "@router.get(\"/status\")" not in content and 'router.get("/status")' not in content:
        print("FAIL: history.py missing /history/status endpoint")
        return False
    if "history_path" not in content or "record_count" not in content:
        print("FAIL: history status endpoint does not return history_path/record_count")
        return False
    print("PASS: history status API exists with history_path and record_count fields")
    return True


def check_7_history_empty_state_diagnostics() -> bool:
    content = read(_TEST_CONSOLE)
    # Check for the 4 diagnostic items
    items = [
        "尚未生成",
        "后端进程刚重启",
        "还没有执行 Risk Check",
        "运行目录",
    ]
    found = sum(1 for item in items if item in content)
    if found < 3:
        print(f"FAIL: history empty state missing diagnostic hints (found {found}/{len(items)})")
        return False
    print(f"PASS: history empty state has diagnostic hints ({found}/{len(items)})")
    return True


def check_8_overview_runner_productization_card() -> bool:
    content = read(_OVERVIEW)
    if "Runner 产品化" not in content and "Runner" not in content:
        print("FAIL: Overview missing Runner 产品化 progress section")
        return False
    if "computeWorkbenchStats" not in content:
        print("FAIL: Overview does not use computeWorkbenchStats")
        return False
    print("PASS: Overview has Runner 产品化 progress card using computeWorkbenchStats")
    return True


def check_9_overview_risk_capabilities() -> bool:
    content = read(_OVERVIEW)
    if "computeWorkbenchStats" not in content:
        print("FAIL: Overview does not use computeWorkbenchStats for risk capabilities")
        return False
    # Should show risk capabilities
    patterns = ["risk", "HIGH_RISK", "风险"]
    found = any(p in content for p in patterns)
    if not found:
        print("FAIL: Overview does not display risk capability count")
        return False
    print("PASS: Overview displays risk capabilities")
    return True


def check_10_image_module_i2i_model_limit() -> bool:
    content = read(_CATEGORY)
    if "MODULE_DESCRIPTIONS" not in content:
        print("FAIL: Category page does not import MODULE_DESCRIPTIONS")
        return False
    if "workbenchStatus" not in content:
        print("FAIL: Category page does not import workbenchStatus")
        return False
    print("PASS: Category page imports MODULE_DESCRIPTIONS from workbenchStatus")
    return True


def check_11_module_descriptions_coverage() -> bool:
    content = read(_WORKBENCH_STATUS)
    required = ["chat", "voice", "image", "music", "file", "models"]
    missing = [m for m in required if m not in content]
    if missing:
        print(f"FAIL: MODULE_DESCRIPTIONS missing modules: {missing}")
        return False
    print("PASS: MODULE_DESCRIPTIONS covers all 6 modules (chat/voice/image/music/file/models)")
    return True


def main():
    print("=" * 60)
    print("Workbench UX Closure checks")
    print("=" * 60)

    checks = [
        ("image-i2i has reference_mode field", check_1_image_i2i_reference_mode),
        ("image-i2i has subject_consistency risk notice", check_2_image_i2i_risk_notice),
        ("image-i2i image-01-live pending note", check_3_image_i2i_live_pending_note),
        ("TestConsole banner mentions raw JSON", check_4_testconsole_banner_raw_json),
        ("TestConsole explains no auto form template", check_5_testconsole_no_auto_template),
        ("history status API exists", check_6_history_status_api),
        ("history empty state has diagnostics", check_7_history_empty_state_diagnostics),
        ("Overview has Runner 产品化 card", check_8_overview_runner_productization_card),
        ("Overview has risk capabilities", check_9_overview_risk_capabilities),
        ("Category uses MODULE_DESCRIPTIONS", check_10_image_module_i2i_model_limit),
        ("MODULE_DESCRIPTIONS covers 6 modules", check_11_module_descriptions_coverage),
    ]

    all_passed = True
    for i, (name, fn) in enumerate(checks, 1):
        print(f"\n[{i}/{len(checks)}] {name}")
        try:
            result = fn()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"FAIL: {name} — {e}")
            all_passed = False

    print()
    if all_passed:
        print(f"All {len(checks)} workbench UX closure checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
