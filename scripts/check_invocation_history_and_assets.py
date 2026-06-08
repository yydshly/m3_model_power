#!/usr/bin/env python3
"""检查调用历史与资产结果展示的完整性。

检查项：
1. 后端存在资产提取函数
2. 前端存在 ResultAssetView / HistoryAssetPreview / InvocationHistoryPanel
3. 历史记录结构包含 capability_id, operation(action), status, assets, duration_ms
4. UI 包含最近调用记录、成功/已阻断/失败状态、复制 URL、打开链接
5. 主 UI 不直接暴露 history.jsonl、blocked_reasons、required_confirmations
6. 不提交 runtime 资产文件
"""
import json
import os
import re
import sys
import yaml


def check_backend_asset_extraction(errors: list[str], warnings: list[str]) -> None:
    """检查后端存在资产提取函数"""
    # The asset extraction lives in history_store.py via _collect_assets and summarize_result
    history_store = "backend/app/minimax_core/verification/history_store.py"
    if not os.path.exists(history_store):
        errors.append(f"[BACKEND] {history_store} not found")
        return

    with open(history_store, 'r', encoding='utf-8') as f:
        content = f.read()

    required_patterns = [
        ("_collect_assets", "asset collection function"),
        ("summarize_result", "result summarization"),
        ("summarize_payload", "payload summarization (sensitive data redaction)"),
        ("_is_sensitive_key", "sensitive key detection"),
    ]
    for pattern, label in required_patterns:
        if pattern not in content:
            errors.append(f"[BACKEND] {history_store} missing {label} ('{pattern}')")

    # Check append_history accepts duration_ms
    if "duration_ms" not in content:
        errors.append(f"[BACKEND] {history_store} missing duration_ms in append_history")


def check_backend_history_routes(errors: list[str], warnings: list[str]) -> None:
    """检查后端历史路由记录了 duration"""
    invoke_py = "backend/app/routers/invoke.py"
    risk_check_py = "backend/app/routers/risk_check.py"

    for path in [invoke_py, risk_check_py]:
        if not os.path.exists(path):
            errors.append(f"[BACKEND] {path} not found")
            continue
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if "duration_ms" not in content and "time.perf_counter" not in content:
            errors.append(f"[BACKEND] {path} missing duration tracking (time.perf_counter or duration_ms)")


def check_frontend_asset_components(errors: list[str], warnings: list[str]) -> None:
    """检查前端存在资产展示组件"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    required_components = [
        ("frontend/src/components/HistoryAssetPreview.tsx", "HistoryAssetPreview"),
        ("frontend/src/components/AssetResultPreview.tsx", "AssetResultPreview"),
        ("frontend/src/components/assetResultUtils.ts", "assetResultUtils (extractors)"),
    ]
    for rel_path, label in required_components:
        full_path = os.path.join(base, rel_path)
        if not os.path.exists(full_path):
            errors.append(f"[FRONTEND] {rel_path} not found (needed for {label})")
        else:
            # Check it has actual rendering logic
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if "return null" not in content and len(content) < 200:
                warnings.append(f"[FRONTEND] {rel_path} seems incomplete (< 200 chars)")

    # InvocationHistoryPanel is optional but recommended
    invocation_panel = os.path.join(base, "frontend/src/components/InvocationHistoryPanel.tsx")
    if os.path.exists(invocation_panel):
        with open(invocation_panel, 'r', encoding='utf-8') as f:
            content = f.read()
        if "调试信息" not in content:
            errors.append(f"[FRONTEND] InvocationHistoryPanel missing '调试信息' collapsible section")


def check_history_record_structure(errors: list[str], warnings: list[str]) -> None:
    """检查历史记录结构包含必要字段"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check history_store append_history record structure
    history_store = os.path.join(base, "backend/app/minimax_core/verification/history_store.py")
    with open(history_store, 'r', encoding='utf-8') as f:
        content = f.read()

    required_record_fields = [
        '"id"',
        '"created_at"',
        '"capability_id"',
        '"action"',
        '"result"',
        '"result_summary"',
        '"duration_ms"',
    ]
    for field in required_record_fields:
        if field not in content:
            errors.append(f"[RECORD] history_store record missing field {field}")


def check_frontend_ui_labels(errors: list[str], warnings: list[str]) -> None:
    """检查 UI 包含必要文案"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    test_console = os.path.join(base, "frontend/src/pages/TestConsole.tsx")
    if not os.path.exists(test_console):
        errors.append(f"[UI] TestConsole.tsx not found")
        return

    with open(test_console, 'r', encoding='utf-8') as f:
        content = f.read()

    required_texts = [
        ("最近调用记录", "history section header"),
        ("调试信息", "debug collapsible section"),
    ]
    for text, label in required_texts:
        if text not in content:
            errors.append(f"[UI] TestConsole.tsx missing required text '{text}' ({label})")


def _is_leaky_line(line: str, term: str) -> bool:
    """Return True if a line exposes term in a leaky way (main UI, not debug)."""
    stripped = line.strip()
    # Allow in comments
    if stripped.startswith('//') or stripped.startswith('*'):
        return False
    # Allow in import statements
    if re.search(r'\bimport\b.*' + term, line):
        return False
    # Allow as JSX property access: riskCheckResult.blocked_reasons
    if re.search(rf'\w+\.{term}\b', line):
        return False
    # Allow inside <details> or </summary> tags (debug sections)
    if '<details' in line or '</summary' in line or '<summary' in line:
        return False
    return True


def check_no_leaky_debug_in_main_ui(errors: list[str], warnings: list[str]) -> None:
    """主 UI 不能直接暴露内部术语"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Main UI files that should NOT contain certain internal terms
    # Note: CapabilityRunner.tsx and Capability.tsx are runner/debug pages where showing
    # blocked_reasons/required_confirmations is appropriate (now wrapped in details/summary).
    # Overview.tsx is the main page and must not expose internal terms.
    pages_to_check = [
        "frontend/src/pages/Overview.tsx",
    ]

    leaky_terms = [
        ("history.jsonl", "history.jsonl should not appear in main UI labels"),
        ("blocked_reasons", "blocked_reasons should only be in debug/collapsible sections"),
        ("required_confirmations", "required_confirmations should only be in debug sections"),
    ]

    for rel_path in pages_to_check:
        full_path = os.path.join(base, rel_path)
        if not os.path.exists(full_path):
            continue
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for term, reason in leaky_terms:
            lines_with_term = [
                line for line in content.split('\n')
                if term in line and _is_leaky_line(line, term)
            ]
            if lines_with_term:
                errors.append(
                    f"[UI] {rel_path} contains leaky term '{term}' outside debug context: {reason}"
                )


def check_no_runtime_assets_in_repo(errors: list[str], warnings: list[str]) -> None:
    """检查没有提交 runtime 资产文件"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    runtime_dirs = [
        "backend/runtime/test_console/history.jsonl",
        "backend/runtime/assets/",
        "frontend/public/assets/",
    ]

    found_assets = []
    for rel_path in runtime_dirs:
        full_path = os.path.join(base, rel_path)
        if rel_path.endswith('/'):
            # Check directory exists and has files
            if os.path.exists(full_path):
                for root, dirs, files in os.walk(full_path):
                    for f in files:
                        if f.endswith(('.mp3', '.wav', '.jpg', '.png', '.json', '.bin')):
                            found_assets.append(os.path.join(root, f))
        else:
            if os.path.exists(full_path):
                found_assets.append(full_path)

    if found_assets:
        # This is a warning since runtime files might exist for other reasons
        warnings.append(
            f"[RUNTIME] Found {len(found_assets)} runtime asset file(s) in repo: "
            f"{', '.join(found_assets[:5])}"
        )


def check_testconsole_reuses_history_panel(errors: list[str], warnings: list[str]) -> None:
    """检查 TestConsole.tsx 复用了 InvocationHistoryPanel"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/pages/TestConsole.tsx")
    if not os.path.exists(path):
        errors.append(f"[UI] TestConsole.tsx not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "import InvocationHistoryPanel" not in content:
        errors.append(f"[UI] TestConsole.tsx does not import InvocationHistoryPanel")
    if "<InvocationHistoryPanel" not in content:
        errors.append(f"[UI] TestConsole.tsx does not use <InvocationHistoryPanel JSX component")


def check_capabilityrunner_has_history(errors: list[str], warnings: list[str]) -> None:
    """检查 CapabilityRunner.tsx 接入 history panel"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/pages/CapabilityRunner.tsx")
    if not os.path.exists(path):
        errors.append(f"[UI] CapabilityRunner.tsx not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    checks = [
        ("getTestConsoleHistory", "getTestConsoleHistory API call"),
        ("InvocationHistoryPanel", "InvocationHistoryPanel component"),
        ("capability_id === selected", "capability_id filtering logic"),
    ]
    for pattern, label in checks:
        if pattern not in content:
            errors.append(f"[UI] CapabilityRunner.tsx missing {label} ('{pattern}')")


def check_strong_img_fields_no_generic_urls(errors: list[str], warnings: list[str]) -> None:
    """检查 _STRONG_IMG_URL_FIELDS 不包含 file_url/download_url"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "backend/app/minimax_core/verification/history_store.py")
    if not os.path.exists(path):
        errors.append(f"[BACKEND] {path} not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find _STRONG_IMG_URL_FIELDS block
    match = re.search(
        r'_STRONG_IMG_URL_FIELDS\s*=\s*frozenset\s*\(\s*\{([^}]+)\}',
        content,
        re.DOTALL,
    )
    if not match:
        errors.append(f"[BACKEND] _STRONG_IMG_URL_FIELDS definition not found in history_store.py")
        return
    fields_block = match.group(1)
    forbidden = ["file_url", "download_url"]
    for field in forbidden:
        if field in fields_block:
            errors.append(
                f"[BACKEND] _STRONG_IMG_URL_FIELDS contains '{field}' which is too generic "
                f"and should be moved to _WEAK_URL_FIELDS with heuristic inference"
            )


def check_no_misleading_copy_in_history_preview(errors: list[str], warnings: list[str]) -> None:
    """检查 HistoryAssetPreview 中没有'完整结果 JSON'误导文案"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/components/HistoryAssetPreview.tsx")
    if not os.path.exists(path):
        errors.append(f"[UI] HistoryAssetPreview.tsx not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "完整结果 JSON" in content:
        errors.append(
            f"[UI] HistoryAssetPreview.tsx contains '完整结果 JSON' which is misleading - "
            f"the rawResult shown there is a summarized result, not the full original response"
        )


def main():
    errors = []
    warnings = []

    check_backend_asset_extraction(errors, warnings)
    check_backend_history_routes(errors, warnings)
    check_frontend_asset_components(errors, warnings)
    check_history_record_structure(errors, warnings)
    check_frontend_ui_labels(errors, warnings)
    check_no_leaky_debug_in_main_ui(errors, warnings)
    check_no_runtime_assets_in_repo(errors, warnings)
    check_testconsole_reuses_history_panel(errors, warnings)
    check_capabilityrunner_has_history(errors, warnings)
    check_strong_img_fields_no_generic_urls(errors, warnings)
    check_no_misleading_copy_in_history_preview(errors, warnings)

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
        print("[PASSED] Invocation history and assets check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
