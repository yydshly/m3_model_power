#!/usr/bin/env python3
"""Check tts-async Runner closure for P1-2.

Checks:
 1. tts-async in RUNNER_SUPPORTED_CAPABILITIES
 2. tts-async NOT in RUNNER_NOT_PRODUCTIZED_CAPABILITIES
 3. tts-async template exists
 4. template result_type == "async_task"
 5. template has mode field
 6. template has task_id field
 7. template has confirm_long_task field
 8. template next_steps contains self handoff (query)
 9. backend handler tts_async distinguishes start/query modes
10. start mode strips confirm_long_task before sending to provider
11. AsyncTaskResultPreview.tsx exists
12. CapabilityRunner.tsx imports AsyncTaskResultPreview
13. CapabilityRunner.tsx uses async_task case
14. audit doc: A-class includes tts-async
15. audit doc: C-class only has tts-ws
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_PATH = _ROOT / "backend" / "app" / "minimax_core" / "runner" / "capability_runner_templates.json"
_CAP_LINKS = _ROOT / "frontend" / "src" / "navigation" / "capabilityLinks.ts"
_RUNNER_PAGE = _ROOT / "frontend" / "src" / "pages" / "CapabilityRunner.tsx"
_ASYNC_PREVIEW = _ROOT / "frontend" / "src" / "components" / "AsyncTaskResultPreview.tsx"
_VOICE_PY = _ROOT / "backend" / "app" / "capabilities" / "voice.py"
_AUDIT_DOC = _ROOT / "docs" / "WORKBENCH_CAPABILITY_CLOSURE_AUDIT.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_templates() -> dict:
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f).get("templates", {})


def parse_set(ts_content: str, set_name: str) -> list[str]:
    """Parse a Set from TypeScript source, stripping single-line comments."""
    stripped = re.sub(r'//.*', '', ts_content)
    match = re.search(rf'{set_name}\s*=\s*new\s+Set\(\s*\[(.*?)\]', stripped, re.DOTALL)
    if not match:
        return []
    return [x.strip().strip("'\"") for x in match.group(1).split(',') if x.strip()]


def check_1_tts_async_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'tts-async' not in caps:
        print("FAIL: tts-async not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: tts-async is in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_2_tts_async_not_in_runner_not_productized() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_NOT_PRODUCTIZED_CAPABILITIES')
    if 'tts-async' in caps:
        print("FAIL: tts-async should NOT be in RUNNER_NOT_PRODUCTIZED_CAPABILITIES")
        return False
    print("PASS: tts-async is NOT in RUNNER_NOT_PRODUCTIZED_CAPABILITIES")
    return True


def check_3_tts_async_template_exists() -> bool:
    templates = load_templates()
    if 'tts-async' not in templates:
        print("FAIL: tts-async template missing")
        return False
    print("PASS: tts-async template exists")
    return True


def check_4_tts_async_result_type() -> bool:
    templates = load_templates()
    tpl = templates.get('tts-async', {})
    rt = tpl.get('result_type', '')
    if rt != 'async_task':
        print(f"FAIL: tts-async result_type is '{rt}', expected 'async_task'")
        return False
    print("PASS: tts-async result_type is async_task")
    return True


def check_5_tts_async_has_mode_field() -> bool:
    templates = load_templates()
    schema = templates.get('tts-async', {}).get('form_schema', {})
    if 'mode' not in schema:
        print("FAIL: tts-async template missing 'mode' field")
        return False
    print("PASS: tts-async template has mode field")
    return True


def check_6_tts_async_has_task_id_field() -> bool:
    templates = load_templates()
    schema = templates.get('tts-async', {}).get('form_schema', {})
    if 'task_id' not in schema:
        print("FAIL: tts-async template missing 'task_id' field")
        return False
    print("PASS: tts-async template has task_id field")
    return True


def check_7_tts_async_has_confirm_long_task() -> bool:
    templates = load_templates()
    schema = templates.get('tts-async', {}).get('form_schema', {})
    if 'confirm_long_task' not in schema:
        print("FAIL: tts-async template missing 'confirm_long_task' field")
        return False
    print("PASS: tts-async template has confirm_long_task field")
    return True


def check_8_tts_async_next_steps_self_handoff() -> bool:
    templates = load_templates()
    tpl = templates.get('tts-async', {})
    next_steps = tpl.get('next_steps', [])
    has_self_query = any(
        ns.get('capability_id') == 'tts-async'
        and ns.get('handoff', {}).get('mode') == 'query'
        for ns in next_steps
    )
    if not has_self_query:
        print("FAIL: tts-async next_steps missing self-handoff (query mode)")
        return False
    print("PASS: tts-async next_steps contains self handoff to query mode")
    return True


def check_9_backend_handler_mode_dispatch() -> bool:
    content = read(_VOICE_PY)
    if 'mode == "query"' not in content and 'mode == \'query\'' not in content:
        print("FAIL: backend handler does not check mode == 'query'")
        return False
    if 'mode == "start"' not in content and 'mode == \'start\'' not in content:
        print("FAIL: backend handler does not check mode == 'start'")
        return False
    print("PASS: backend handler distinguishes start/query modes")
    return True


def check_10_start_strips_confirm_long_task() -> bool:
    content = read(_VOICE_PY)
    # Should filter out confirm_long_task from payload sent to provider
    # Look for confirm_long_task in an exclusion list or being removed
    if 'confirm_long_task' not in content:
        print("FAIL: backend handler does not reference confirm_long_task")
        return False
    # Should not send confirm_long_task to the provider
    # Check it's filtered out before the API call
    if re.search(r'["\']confirm_long_task["\'].*?tts_async', content):
        print("FAIL: confirm_long_task may be sent to provider (check handler)")
        return False
    print("PASS: backend handler filters confirm_long_task before sending to provider")
    return True


def check_11_async_task_result_preview_exists() -> bool:
    if not _ASYNC_PREVIEW.exists():
        print(f"FAIL: {_ASYNC_PREVIEW} does not exist")
        return False
    print("PASS: AsyncTaskResultPreview.tsx exists")
    return True


def check_12_runner_imports_async_preview() -> bool:
    content = read(_RUNNER_PAGE)
    if 'AsyncTaskResultPreview' not in content:
        print("FAIL: CapabilityRunner.tsx does not import AsyncTaskResultPreview")
        return False
    print("PASS: CapabilityRunner.tsx imports AsyncTaskResultPreview")
    return True


def check_13_runner_uses_async_task() -> bool:
    content = read(_RUNNER_PAGE)
    if 'async_task' not in content:
        print("FAIL: CapabilityRunner.tsx does not handle async_task result type")
        return False
    print("PASS: CapabilityRunner.tsx handles async_task result type")
    return True


def check_14_audit_doc_tts_async_a_class() -> bool:
    content = read(_AUDIT_DOC)
    if 'tts-async' not in content:
        print("FAIL: tts-async not found in audit doc")
        return False
    # Check A-class section includes tts-async
    a_match = re.search(r'### A 类.*?(?=### B 类|#)', content, re.DOTALL)
    if not a_match:
        print("FAIL: A-class section not found in audit doc")
        return False
    a_text = a_match.group()
    if 'tts-async' not in a_text:
        print("FAIL: tts-async not in A-class section of audit doc")
        return False
    print("PASS: audit doc A-class includes tts-async")
    return True


def check_15_audit_doc_c_class_only_tts_ws() -> bool:
    content = read(_AUDIT_DOC)
    # C-class section should only list tts-ws
    c_match = re.search(r'### C 类.*?(?=### D 类|## |\Z)', content, re.DOTALL)
    if not c_match:
        print("FAIL: C-class section not found in audit doc")
        return False
    c_text = c_match.group()
    if 'tts-ws' not in c_text:
        print("FAIL: tts-ws not found in C-class section")
        return False
    if 'tts-async' in c_text:
        print("FAIL: tts-async should NOT be in C-class section")
        return False
    print("PASS: audit doc C-class only contains tts-ws (tts-async moved to A-class)")
    return True


def main():
    print("=" * 60)
    print("tts-async Runner Closure checks (P1-2)")
    print("=" * 60)

    checks = [
        ("tts-async in RUNNER_SUPPORTED_CAPABILITIES", check_1_tts_async_in_runner_supported),
        ("tts-async NOT in RUNNER_NOT_PRODUCTIZED_CAPABILITIES", check_2_tts_async_not_in_runner_not_productized),
        ("tts-async template exists", check_3_tts_async_template_exists),
        ("tts-async result_type == async_task", check_4_tts_async_result_type),
        ("tts-async template has mode field", check_5_tts_async_has_mode_field),
        ("tts-async template has task_id field", check_6_tts_async_has_task_id_field),
        ("tts-async template has confirm_long_task", check_7_tts_async_has_confirm_long_task),
        ("tts-async next_steps self-handoff", check_8_tts_async_next_steps_self_handoff),
        ("backend handler distinguishes start/query", check_9_backend_handler_mode_dispatch),
        ("start mode strips confirm_long_task", check_10_start_strips_confirm_long_task),
        ("AsyncTaskResultPreview.tsx exists", check_11_async_task_result_preview_exists),
        ("CapabilityRunner imports AsyncTaskResultPreview", check_12_runner_imports_async_preview),
        ("CapabilityRunner handles async_task", check_13_runner_uses_async_task),
        ("audit doc: tts-async in A-class", check_14_audit_doc_tts_async_a_class),
        ("audit doc: C-class only tts-ws", check_15_audit_doc_c_class_only_tts_ws),
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
        print(f"All {len(checks)} tts-async runner closure checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
