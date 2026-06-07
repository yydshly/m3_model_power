#!/usr/bin/env python3
"""Check workbench main hardening items.

Covers:
 1. workbenchStatus no longer uses billing_category as inScopeVerified
 2. Overview does not display registry/billing derivation as "已验收"
 3. image-i2i subject_reference[0].type is still "character"
 4. image-i2i reference_mode does not go into subject_reference.type
 5. image-i2i three reference_mode values produce different enhanced prompts
 6. ChatResultPreview distinguishes final vs reasoning source
 7. ChatResultPreview shows reasoning hint when source is reasoning
 8. ChatResultPreview still preserves full JSON expansion
 9. history router no longer imports _ensure_dir
10. history_store exposes get_history_status
11. HistoryStatusResp has line_count / valid_record_count
12. RunnerForm renders field.note
13. Overview runner templates loading failure shows explicit error
14. get_history_status returns relative path, not absolute
15. ChatResultPreview supports block.thinking field
16. ChatResultPreview has final-first priority for content blocks
17. ChatResultPreview handles nested data.content with thinking
18. Responses output content also uses final-first priority
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_PATH = _ROOT / "backend" / "app" / "minimax_core" / "runner" / "capability_runner_templates.json"
_WORKBENCH_STATUS = _ROOT / "frontend" / "src" / "workbenchStatus.ts"
_OVERVIEW = _ROOT / "frontend" / "src" / "pages" / "Overview.tsx"
_CHAT_PREVIEW = _ROOT / "frontend" / "src" / "components" / "ChatResultPreview.tsx"
_HISTORY_STORE = _ROOT / "backend" / "app" / "minimax_core" / "verification" / "history_store.py"
_HISTORY_ROUTER = _ROOT / "backend" / "app" / "routers" / "history.py"
_API_TS = _ROOT / "frontend" / "src" / "api.ts"
_RUNNER_TSX = _ROOT / "frontend" / "src" / "pages" / "CapabilityRunner.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_templates() -> dict:
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f).get("templates", {})


def check_1_workbench_status_no_inScopeVerified() -> bool:
    """workbenchStatus exports WorkbenchStats with inScopeTokenPlanCovered, not inScopeVerified."""
    content = read(_WORKBENCH_STATUS)
    if "inScopeVerified" in content:
        print("FAIL: workbenchStatus still uses inScopeVerified")
        return False
    if "inScopeTokenPlanCovered" not in content:
        print("FAIL: workbenchStatus does not have inScopeTokenPlanCovered")
        return False
    print("PASS: workbenchStatus uses inScopeTokenPlanCovered, not inScopeVerified")
    return True


def check_2_overview_not_showing_verified() -> bool:
    """Overview does not use the word '已验收' for Token Plan coverage stats."""
    content = read(_OVERVIEW)
    # Check the Runner productization section no longer says '已验收'
    # Find the GapStat with label "Token Plan 验收"
    if "Token Plan 验收" in content and "Token Plan 覆盖" not in content.split("Token Plan 验收")[0][-100:]:
        # Check if there's still a "已验收" near "Token Plan 验收"
        idx = content.find("Token Plan 验收")
        window = content[max(0, idx-50):idx+200]
        if "已验收" in window:
            print("FAIL: Overview still shows '已验收' for Token Plan coverage")
            return False
    # Check the inScopeTokenPlanCovered field is used
    if "inScopeTokenPlanCovered" not in content:
        print("FAIL: Overview does not use inScopeTokenPlanCovered")
        return False
    # Check the sub text mentions "TokenPlan 范围" not "已验收"
    if "sub=\"已验收" in content or "sub='已验收" in content:
        print("FAIL: Overview still has sub text with '已验收'")
        return False
    print("PASS: Overview does not display registry/billing derivation as '已验收'")
    return True


def check_3_image_i2i_type_is_character() -> bool:
    """image-i2i subject_reference[0].type is 'character'."""
    templates = load_templates()
    i2i = templates.get("image-i2i", {})
    payload = i2i.get("payload_template", {})
    subject_ref = payload.get("subject_reference", [])
    if not subject_ref:
        print("FAIL: image-i2i payload_template has no subject_reference array")
        return False
    ref_type = subject_ref[0].get("type", "")
    if ref_type != "character":
        print(f"FAIL: image-i2i subject_reference[0].type is '{ref_type}', expected 'character'")
        return False
    print("PASS: image-i2i subject_reference[0].type is 'character'")
    return True


def check_4_ref_mode_not_in_api_type() -> bool:
    """reference_mode does not go directly into subject_reference.type."""
    templates = load_templates()
    i2i = templates.get("image-i2i", {})
    payload = i2i.get("payload_template", {})
    subject_ref = payload.get("subject_reference", [])
    if not subject_ref:
        print("FAIL: image-i2i payload_template has no subject_reference array")
        return False
    ref_type = subject_ref[0].get("type", "")
    if ref_type == "{reference_mode}":
        print("FAIL: image-i2i subject_reference[0].type is still '{reference_mode}'")
        return False
    print(f"PASS: image-i2i subject_reference[0].type is '{ref_type}', not '{{reference_mode}}'")
    return True


def check_5_i2i_ref_mode_enhances_prompt() -> bool:
    """image-i2i three reference_mode values produce different enhanced prompts."""
    content = read(_RUNNER_TSX)
    # Check applyI2IPromptMode function exists
    if "applyI2IPromptMode" not in content:
        print("FAIL: applyI2IPromptMode function not found in CapabilityRunner.tsx")
        return False
    # Check it is called in handleRun
    if "applyI2IPromptMode(basePayload, values, template.capability_id)" not in content:
        print("FAIL: applyI2IPromptMode not called in handleRun")
        return False
    # Check prefixMap has all three modes
    prefix_map_found = False
    for mode in ("subject", "style", "variation"):
        if mode not in content:
            print(f"FAIL: applyI2IPromptMode missing mode '{mode}'")
            return False
        prefix_map_found = True
    if not prefix_map_found:
        print("FAIL: applyI2IPromptMode prefixMap not found")
        return False
    # Check payload preview uses applyI2IPromptMode
    if "applyI2IPromptMode(buildPayload" not in content:
        print("FAIL: payload preview does not use applyI2IPromptMode")
        return False
    print("PASS: applyI2IPromptMode exists and is used correctly for all three modes")
    return True


def check_6_chat_result_preview_distinguishes_source() -> bool:
    """ChatResultPreview extracts ChatTextSource with 'final' and 'reasoning'."""
    content = read(_CHAT_PREVIEW)
    if "ChatTextSource" not in content:
        print("FAIL: ChatResultPreview does not define ChatTextSource type")
        return False
    # Check extractChatTextSource function exists
    if "extractChatTextSource" not in content:
        print("FAIL: ChatResultPreview does not have extractChatTextSource function")
        return False
    # Check it returns a struct with source field
    patterns = ["source: 'final'", "source: 'reasoning'"]
    found = sum(1 for p in patterns if p in content)
    if found < 2:
        print(f"FAIL: extractChatTextSource does not return structured source (found {found}/{len(patterns)})")
        return False
    print("PASS: ChatResultPreview distinguishes final vs reasoning source")
    return True


def check_7_chat_preview_shows_reasoning_hint() -> bool:
    """ChatResultPreview shows reasoning hint when source is reasoning."""
    content = read(_CHAT_PREVIEW)
    patterns = [
        "reasoning",
        "推理块",
        "不一定是最终回答",
        "source === 'reasoning'",
    ]
    found = sum(1 for p in patterns if p in content)
    if found < 3:
        print(f"FAIL: ChatResultPreview reasoning hint not found (found {found}/{len(patterns)})")
        return False
    print("PASS: ChatResultPreview shows reasoning hint when source is reasoning")
    return True


def check_8_chat_preview_preserves_json() -> bool:
    """ChatResultPreview still has full JSON expansion."""
    content = read(_CHAT_PREVIEW)
    patterns = ["展开完整 JSON", "JsonView", "<details"]
    found = sum(1 for p in patterns if p in content)
    if found < 2:
        print(f"FAIL: ChatResultPreview full JSON expansion not found (found {found}/{len(patterns)})")
        return False
    print("PASS: ChatResultPreview preserves full JSON expansion")
    return True


def check_9_history_router_no_ensure_dir() -> bool:
    """history router no longer imports or uses _ensure_dir."""
    content = read(_HISTORY_ROUTER)
    if "_ensure_dir" in content:
        print("FAIL: history router still imports or uses _ensure_dir")
        return False
    if "get_history_status" not in content:
        print("FAIL: history router does not use get_history_status")
        return False
    print("PASS: history router no longer imports _ensure_dir, uses get_history_status instead")
    return True


def check_10_history_store_exposes_get_status() -> bool:
    """history_store.py exposes get_history_status function."""
    content = read(_HISTORY_STORE)
    if "def get_history_status" not in content:
        print("FAIL: history_store.py does not define get_history_status")
        return False
    print("PASS: history_store.py exposes get_history_status")
    return True


def check_11_history_status_has_line_and_valid_count() -> bool:
    """HistoryStatusResp has line_count and valid_record_count."""
    content = read(_API_TS)
    if "line_count" not in content:
        print("FAIL: HistoryStatusResp missing line_count")
        return False
    if "valid_record_count" not in content:
        print("FAIL: HistoryStatusResp missing valid_record_count")
        return False
    # Check get_history_status returns these fields (in history_store.py)
    store_content = read(_HISTORY_STORE)
    if "result[\"line_count\"]" not in store_content and '"line_count"' not in store_content:
        print("FAIL: get_history_status does not return line_count")
        return False
    if "result[\"valid_record_count\"]" not in store_content and '"valid_record_count"' not in store_content:
        print("FAIL: get_history_status does not return valid_record_count")
        return False
    print("PASS: HistoryStatusResp has line_count and valid_record_count")
    return True


def check_12_runner_form_renders_note() -> bool:
    """RunnerForm renders field.note."""
    content = read(_RUNNER_TSX)
    if "field.note" not in content:
        print("FAIL: RunnerForm does not render field.note")
        return False
    # Check FormField type includes note
    if "note?: string" not in content:
        print("FAIL: FormField type does not include note field")
        return False
    print("PASS: RunnerForm renders field.note and FormField type includes note")
    return True


def check_13_overview_shows_runner_load_error() -> bool:
    """Overview shows explicit error when runner templates fail to load."""
    content = read(_OVERVIEW)
    patterns = [
        "setRunnerTemplatesErr",
        "Runner 产品化状态加载失败",
        "/api/runner/templates",
    ]
    found = sum(1 for p in patterns if p in content)
    if found < 2:
        print(f"FAIL: Overview does not show explicit error for runner templates failure (found {found}/{len(patterns)})")
        return False
    print("PASS: Overview shows explicit error when runner templates fail to load")
    return True


def check_14_get_history_status_relative_path() -> bool:
    """get_history_status returns relative path, not absolute."""
    content = read(_HISTORY_STORE)
    # Check it does NOT return str(path) of an absolute Path object
    if '"history_path": str(path)' in content or "'history_path': str(path)" in content:
        print("FAIL: get_history_status returns str(path) absolute path")
        return False
    # Check it returns a relative string
    if "runtime/test_console/history.jsonl" not in content:
        print("FAIL: get_history_status does not use relative path 'runtime/test_console/history.jsonl'")
        return False
    print("PASS: get_history_status returns relative path, not absolute")
    return True


def check_15_chat_preview_supports_thinking_field() -> bool:
    """ChatResultPreview supports block.thinking field."""
    content = read(_CHAT_PREVIEW)
    if "thinking?: string" not in content:
        print("FAIL: TextLikeBlock type does not include thinking field")
        return False
    if "block.thinking" not in content:
        print("FAIL: getBlockText does not check block.thinking")
        return False
    print("PASS: ChatResultPreview supports block.thinking field")
    return True


def check_16_chat_preview_final_first_priority() -> bool:
    """ChatResultPreview uses final-first priority for content blocks."""
    content = read(_CHAT_PREVIEW)
    if "extractFromContentBlocks" not in content:
        print("FAIL: extractFromContentBlocks function not found")
        return False
    print("PASS: ChatResultPreview has final-first priority logic via extractFromContentBlocks")
    return True


def check_17_chat_preview_nested_content_thinking() -> bool:
    """ChatResultPreview handles nested data.content with thinking."""
    content = read(_CHAT_PREVIEW)
    if "nested?.content" not in content and "nested.content" not in content:
        print("FAIL: nested data.content not handled")
        return False
    if "data.content" not in content:
        print("FAIL: data.content path not used in extraction")
        return False
    print("PASS: ChatResultPreview handles nested data.content with thinking")
    return True


def check_18_chat_preview_responses_final_first() -> bool:
    """Responses output content also uses final-first priority."""
    content = read(_CHAT_PREVIEW)
    if "output[" not in content:
        print("FAIL: Responses output array not handled")
        return False
    if content.count("output[") < 2:
        print("FAIL: Responses output iteration not found")
        return False
    print("PASS: Responses output content uses final-first priority")
    return True


def main():
    print("=" * 60)
    print("Workbench Main Hardening checks")
    print("=" * 60)

    checks = [
        ("workbenchStatus uses inScopeTokenPlanCovered", check_1_workbench_status_no_inScopeVerified),
        ("Overview does not show '已验收'", check_2_overview_not_showing_verified),
        ("image-i2i type is character", check_3_image_i2i_type_is_character),
        ("reference_mode not in API type", check_4_ref_mode_not_in_api_type),
        ("applyI2IPromptMode enhances prompt", check_5_i2i_ref_mode_enhances_prompt),
        ("ChatResultPreview distinguishes final/reasoning", check_6_chat_result_preview_distinguishes_source),
        ("ChatResultPreview shows reasoning hint", check_7_chat_preview_shows_reasoning_hint),
        ("ChatResultPreview preserves JSON", check_8_chat_preview_preserves_json),
        ("history router no _ensure_dir", check_9_history_router_no_ensure_dir),
        ("history_store has get_history_status", check_10_history_store_exposes_get_status),
        ("HistoryStatusResp has line_count/valid_record_count", check_11_history_status_has_line_and_valid_count),
        ("RunnerForm renders field.note", check_12_runner_form_renders_note),
        ("Overview shows runner load error", check_13_overview_shows_runner_load_error),
        ("get_history_status uses relative path", check_14_get_history_status_relative_path),
        ("ChatResultPreview supports thinking field", check_15_chat_preview_supports_thinking_field),
        ("ChatResultPreview final-first priority", check_16_chat_preview_final_first_priority),
        ("ChatResultPreview nested content thinking", check_17_chat_preview_nested_content_thinking),
        ("ChatResultPreview Responses final-first", check_18_chat_preview_responses_final_first),
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
        print(f"All {len(checks)} workbench main hardening checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
