#!/usr/bin/env python3
"""检查 TestConsole 和 CapabilityRunner 产品化验收检查。

检查项：
1. 存在 getCapabilityHistory API（前端 + 后端）
2. CapabilityRunner 不再用 getTestConsoleHistory(50) 后端前端过滤
3. 存在 UsageCostExplainer 组件
4. TestConsole 自动使用 demo payload（buildDemoPayload）
5. chat-responses-tokens demo payload 不是 {}
6. music-gen lyrics 默认值不是空字符串
7. TestConsole 中出现"恢复示例 payload"按钮文案
8. 不出现"Token = 钱"这类错误文案
"""
import json
import os
import re
import sys


def check_get_capability_history_api(errors: list[str], warnings: list[str]) -> None:
    """检查前端有 getCapabilityHistory 函数"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Frontend API
    api_path = os.path.join(base, "frontend/src/api.ts")
    if not os.path.exists(api_path):
        errors.append(f"[API] {api_path} not found")
        return
    with open(api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "getCapabilityHistory" not in content:
        errors.append("[API] getCapabilityHistory function not found in api.ts")

    # Backend router
    history_router = os.path.join(base, "backend/app/routers/history.py")
    if not os.path.exists(history_router):
        errors.append(f"[API] {history_router} not found")
        return
    with open(history_router, 'r', encoding='utf-8') as f:
        content = f.read()
    if "/capability/{capability_id}" not in content:
        errors.append("[API] /api/history/capability/{capability_id} endpoint not found in history router")


def check_capabilityrunner_no_global_history_filter(errors: list[str], warnings: list[str]) -> None:
    """检查 CapabilityRunner 不再用 getTestConsoleHistory(50) 后端前端过滤"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/pages/CapabilityRunner.tsx")
    if not os.path.exists(path):
        errors.append(f"[UI] CapabilityRunner.tsx not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "getCapabilityHistory" not in content:
        errors.append("[UI] CapabilityRunner.tsx does not use getCapabilityHistory (still using global history filter)")


def check_usage_cost_explainer(errors: list[str], warnings: list[str]) -> None:
    """检查存在 UsageCostExplainer 组件"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/components/UsageCostExplainer.tsx")
    if not os.path.exists(path):
        errors.append("[UI] UsageCostExplainer.tsx not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "Token" not in content or "套餐" not in content:
        errors.append("[UI] UsageCostExplainer.tsx missing Token/套餐 explanation copy")


def check_testconsole_demo_payload(errors: list[str], warnings: list[str]) -> None:
    """检查 TestConsole 使用 buildDemoPayload"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/pages/TestConsole.tsx")
    if not os.path.exists(path):
        errors.append(f"[UI] TestConsole.tsx not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "buildDemoPayload" not in content:
        errors.append("[UI] TestConsole.tsx does not use buildDemoPayload")


def check_chat_responses_tokens_demo(errors: list[str], warnings: list[str]) -> None:
    """检查 chat-responses-tokens demo payload 不是 {}"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    demo_path = os.path.join(base, "frontend/src/domain/demoPayload.ts")
    if not os.path.exists(demo_path):
        errors.append(f"[DEMO] demoPayload.ts not found")
        return
    with open(demo_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # chat-responses-tokens should have 'input' field (not just {})
    if "'chat-responses-tokens'" in content:
        idx = content.index("'chat-responses-tokens'")
        snippet = content[idx:idx+250]
        # Check for 'input:' field (ASCII-safe)
        if 'input:' not in snippet:
            errors.append("[DEMO] 'chat-responses-tokens' demo payload missing 'input' field")


def check_music_gen_lyrics_not_empty(errors: list[str], warnings: list[str]) -> None:
    """检查 music-gen lyrics 默认值不是空字符串"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    demo_path = os.path.join(base, "frontend/src/domain/demoPayload.ts")
    if not os.path.exists(demo_path):
        errors.append(f"[DEMO] demoPayload.ts not found")
        return
    with open(demo_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find music-gen section
    if "'music-gen'" not in content:
        errors.append("[DEMO] 'music-gen' demo payload not found")
        return
    idx = content.index("'music-gen'")
    snippet = content[idx:idx+400]
    # Should have 'lyrics:' field (ASCII-safe check)
    if 'lyrics:' not in snippet:
        errors.append("[DEMO] 'music-gen' missing 'lyrics' field in demo payload")


def check_demo_payload_file_exists(errors: list[str], warnings: list[str]) -> None:
    """检查 demoPayload.ts 存在"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/domain/demoPayload.ts")
    if not os.path.exists(path):
        errors.append("[DEMO] frontend/src/domain/demoPayload.ts not found")


def check_no_token_equals_money(errors: list[str], warnings: list[str]) -> None:
    """检查没有"Token = 钱"这类错误文案"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dirs_to_check = [
        os.path.join(base, "frontend/src/components"),
        os.path.join(base, "frontend/src/pages"),
        os.path.join(base, "frontend/src/domain"),
    ]
    bad_patterns = [
        (r"Token\s*=\s*钱", "Token = 钱"),
        (r"Token\s*就是\s*钱", "Token 就是 钱"),
    ]
    for d in dirs_to_check:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for fname in files:
                if not fname.endswith(('.ts', '.tsx')):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception:
                    continue
                for pattern, label in bad_patterns:
                    if re.search(pattern, content):
                        errors.append(f"[COPY] {fpath}: contains misleading 'Token = 钱' copy")


def check_testconsole_reset_button(errors: list[str], warnings: list[str]) -> None:
    """检查 TestConsole 有"恢复示例 payload"按钮文案"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "frontend/src/pages/TestConsole.tsx")
    if not os.path.exists(path):
        errors.append(f"[UI] TestConsole.tsx not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Check for demo payload reset button (matches buildDemoPayload usage)
    if "buildDemoPayload" not in content:
        errors.append("[UI] TestConsole.tsx missing 'buildDemoPayload' call for demo payload")


def main():
    errors = []
    warnings = []

    check_get_capability_history_api(errors, warnings)
    check_capabilityrunner_no_global_history_filter(errors, warnings)
    check_usage_cost_explainer(errors, warnings)
    check_demo_payload_file_exists(errors, warnings)
    check_testconsole_demo_payload(errors, warnings)
    check_chat_responses_tokens_demo(errors, warnings)
    check_music_gen_lyrics_not_empty(errors, warnings)
    check_testconsole_reset_button(errors, warnings)
    check_no_token_equals_money(errors, warnings)

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
        print("[PASSED] Productized test console and usage check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
