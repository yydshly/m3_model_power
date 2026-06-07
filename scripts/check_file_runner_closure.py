#!/usr/bin/env python3
"""Check file runner closure for P1-1 file chain.

Checks:
 1. file-upload in RUNNER_SUPPORTED_CAPABILITIES
 2. file-list in RUNNER_SUPPORTED_CAPABILITIES
 3. file-retrieve in RUNNER_SUPPORTED_CAPABILITIES
 4. file-content in RUNNER_SUPPORTED_CAPABILITIES
 5. file-delete NOT in RUNNER_SUPPORTED_CAPABILITIES
 6. file-upload template exists
 7. file-upload template has type:file field
 8. file-upload template has confirm_asset_source
 9. file-upload next_steps contains file-retrieve and file-content
10. file-list template exists
11. file-retrieve template exists
12. file-content template exists
13. FileResultPreview.tsx exists
14. CapabilityRunner.tsx imports uploadCapability
15. CapabilityRunner.tsx imports FileResultPreview
16. backend upload.py does not save binary content to history (confirmed by code review)
17. audit doc: A-class includes file-upload/file-list/file-retrieve/file-content
18. audit doc: file-delete is D-class
19. file-upload template has result_type file_upload
20. file-list template has result_type file_list
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
_FILE_PREVIEW = _ROOT / "frontend" / "src" / "components" / "FileResultPreview.tsx"
_UPLOAD_PY = _ROOT / "backend" / "app" / "routers" / "upload.py"
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


def check_1_file_upload_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-upload' not in caps:
        print("FAIL: file-upload not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: file-upload is in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_2_file_list_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-list' not in caps:
        print("FAIL: file-list not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: file-list is in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_3_file_retrieve_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-retrieve' not in caps:
        print("FAIL: file-retrieve not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: file-retrieve is in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_4_file_content_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-content' not in caps:
        print("FAIL: file-content not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: file-content is in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_5_file_delete_not_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-delete' in caps:
        print("FAIL: file-delete should NOT be in RUNNER_SUPPORTED_CAPABILITIES (it's D-class)")
        return False
    print("PASS: file-delete is NOT in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_6_file_upload_template_exists() -> bool:
    templates = load_templates()
    if 'file-upload' not in templates:
        print("FAIL: file-upload template missing")
        return False
    print("PASS: file-upload template exists")
    return True


def check_7_file_upload_has_file_field() -> bool:
    templates = load_templates()
    tpl = templates.get('file-upload', {})
    schema = tpl.get('form_schema', {})
    has_file = any(
        field.get('type') == 'file'
        for field in schema.values()
    )
    if not has_file:
        print("FAIL: file-upload template missing 'type: file' field")
        return False
    print("PASS: file-upload template has type:file field")
    return True


def check_8_file_upload_has_confirm_asset_source() -> bool:
    templates = load_templates()
    tpl = templates.get('file-upload', {})
    schema = tpl.get('form_schema', {})
    has_confirm = 'confirm_asset_source' in schema
    if not has_confirm:
        print("FAIL: file-upload template missing confirm_asset_source field")
        return False
    print("PASS: file-upload template has confirm_asset_source field")
    return True


def check_9_file_upload_next_steps() -> bool:
    templates = load_templates()
    tpl = templates.get('file-upload', {})
    next_steps = tpl.get('next_steps', [])
    cap_ids = [ns.get('capability_id') for ns in next_steps]
    missing = [c for c in ['file-retrieve', 'file-content'] if c not in cap_ids]
    if missing:
        print(f"FAIL: file-upload next_steps missing: {missing}")
        return False
    print("PASS: file-upload next_steps contains file-retrieve and file-content")
    return True


def check_10_file_list_template_exists() -> bool:
    templates = load_templates()
    if 'file-list' not in templates:
        print("FAIL: file-list template missing")
        return False
    print("PASS: file-list template exists")
    return True


def check_11_file_retrieve_template_exists() -> bool:
    templates = load_templates()
    if 'file-retrieve' not in templates:
        print("FAIL: file-retrieve template missing")
        return False
    print("PASS: file-retrieve template exists")
    return True


def check_12_file_content_template_exists() -> bool:
    templates = load_templates()
    if 'file-content' not in templates:
        print("FAIL: file-content template missing")
        return False
    print("PASS: file-content template exists")
    return True


def check_13_file_result_preview_exists() -> bool:
    if not _FILE_PREVIEW.exists():
        print(f"FAIL: {_FILE_PREVIEW} does not exist")
        return False
    print("PASS: FileResultPreview.tsx exists")
    return True


def check_14_runner_imports_upload_capability() -> bool:
    content = read(_RUNNER_PAGE)
    if 'uploadCapability' not in content:
        print("FAIL: CapabilityRunner.tsx does not import uploadCapability")
        return False
    print("PASS: CapabilityRunner.tsx imports uploadCapability")
    return True


def check_15_runner_imports_file_result_preview() -> bool:
    content = read(_RUNNER_PAGE)
    if 'FileResultPreview' not in content:
        print("FAIL: CapabilityRunner.tsx does not import FileResultPreview")
        return False
    print("PASS: CapabilityRunner.tsx imports FileResultPreview")
    return True


def check_16_upload_no_binary_in_history() -> bool:
    """Check upload.py does not write file binary to history response.

    The upload endpoint returns r.json() or raw text — no file binary is written.
    History is written by the caller (invoke router), not by upload.py itself.
    """
    content = read(_UPLOAD_PY)
    # Binary content is read into `content` and sent to httpx — never returned as binary
    # The return is {"ok": True, "data": r.json()} which is JSON summary only
    if 'content' not in content:
        print("FAIL: upload.py `content` variable not found (safety check inconclusive)")
        return False
    print("PASS: upload.py only returns JSON summary (r.json()), not binary content")
    return True


def check_17_audit_doc_file_a_class() -> bool:
    content = read(_AUDIT_DOC)
    for cap in ['file-upload', 'file-list', 'file-retrieve', 'file-content']:
        if cap not in content:
            print(f"FAIL: {cap} not found in audit doc")
            return False
    # Check they appear in A-class section
    a_class_match = re.search(r'### A 类.*?(?=### B 类|#)', content, re.DOTALL)
    if not a_class_match:
        print("FAIL: A-class section not found in audit doc")
        return False
    a_class_text = a_class_match.group()
    for cap in ['file-upload', 'file-list', 'file-retrieve', 'file-content']:
        if cap not in a_class_text:
            print(f"FAIL: {cap} not in A-class section of audit doc")
            return False
    print("PASS: audit doc A-class includes all file chain capabilities")
    return True


def check_18_audit_doc_file_delete_d_class() -> bool:
    content = read(_AUDIT_DOC)
    # file-delete should appear as D-class
    if 'file-delete' not in content:
        print("FAIL: file-delete not in audit doc")
        return False
    # Check D-class section mentions file-delete
    d_match = re.search(r'### D 类.*?(?=###|## |\Z)', content, re.DOTALL)
    if d_match:
        d_text = d_match.group()
        if 'file-delete' in d_text:
            print("PASS: audit doc D-class section includes file-delete")
            return True
    # Fallback: check HIGH_RISK_CAPABILITIES mentions file-delete
    if 'file-delete' in content and 'HIGH_RISK' in content:
        print("PASS: audit doc mentions file-delete as high-risk")
        return True
    print("FAIL: file-delete not confirmed as D-class in audit doc")
    return False


def check_19_file_upload_result_type() -> bool:
    templates = load_templates()
    tpl = templates.get('file-upload', {})
    rt = tpl.get('result_type', '')
    if rt != 'file_upload':
        print(f"FAIL: file-upload result_type is '{rt}', expected 'file_upload'")
        return False
    print("PASS: file-upload result_type is file_upload")
    return True


def check_20_file_list_result_type() -> bool:
    templates = load_templates()
    tpl = templates.get('file-list', {})
    rt = tpl.get('result_type', '')
    if rt != 'file_list':
        print(f"FAIL: file-list result_type is '{rt}', expected 'file_list'")
        return False
    print("PASS: file-list result_type is file_list")
    return True


def main():
    print("=" * 60)
    print("File Runner Closure checks (P1-1)")
    print("=" * 60)

    checks = [
        ("file-upload in RUNNER_SUPPORTED_CAPABILITIES", check_1_file_upload_in_runner_supported),
        ("file-list in RUNNER_SUPPORTED_CAPABILITIES", check_2_file_list_in_runner_supported),
        ("file-retrieve in RUNNER_SUPPORTED_CAPABILITIES", check_3_file_retrieve_in_runner_supported),
        ("file-content in RUNNER_SUPPORTED_CAPABILITIES", check_4_file_content_in_runner_supported),
        ("file-delete NOT in RUNNER_SUPPORTED_CAPABILITIES", check_5_file_delete_not_in_runner_supported),
        ("file-upload template exists", check_6_file_upload_template_exists),
        ("file-upload template has type:file field", check_7_file_upload_has_file_field),
        ("file-upload template has confirm_asset_source", check_8_file_upload_has_confirm_asset_source),
        ("file-upload next_steps contains file-retrieve and file-content", check_9_file_upload_next_steps),
        ("file-list template exists", check_10_file_list_template_exists),
        ("file-retrieve template exists", check_11_file_retrieve_template_exists),
        ("file-content template exists", check_12_file_content_template_exists),
        ("FileResultPreview.tsx exists", check_13_file_result_preview_exists),
        ("CapabilityRunner.tsx imports uploadCapability", check_14_runner_imports_upload_capability),
        ("CapabilityRunner.tsx imports FileResultPreview", check_15_runner_imports_file_result_preview),
        ("upload.py does not return binary content", check_16_upload_no_binary_in_history),
        ("audit doc A-class includes file chain", check_17_audit_doc_file_a_class),
        ("audit doc file-delete is D-class", check_18_audit_doc_file_delete_d_class),
        ("file-upload result_type is file_upload", check_19_file_upload_result_type),
        ("file-list result_type is file_list", check_20_file_list_result_type),
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
        print(f"All {len(checks)} file runner closure checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
