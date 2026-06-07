#!/usr/bin/env python3
"""检查 quota_sensitive 确认项 UI 是否正确实现。"""
import os
import re
import sys

def main():
    errors = []
    warnings = []

    # 1. confirmations.ts 必须存在
    if not os.path.exists('frontend/src/domain/confirmations.ts'):
        errors.append("frontend/src/domain/confirmations.ts does not exist")
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1

    with open('frontend/src/domain/confirmations.ts', 'r', encoding='utf-8') as f:
        confirmations_content = f.read()

    # 2. 必须包含 quota_sensitive 判断逻辑
    if "billing_category === 'quota_sensitive'" not in confirmations_content:
        errors.append("confirmations.ts missing billing_category === 'quota_sensitive' check")
    if 'requires_explicit_confirmation' not in confirmations_content:
        errors.append("confirmations.ts missing requires_explicit_confirmation check")
    if 'confirm_quota' not in confirmations_content:
        errors.append("confirmations.ts missing confirm_quota")

    # 3. Capability.tsx、InvokePanel.tsx、TestConsole.tsx 必须 import confirmations.ts
    for filepath in [
        'frontend/src/pages/Capability.tsx',
        'frontend/src/components/InvokePanel.tsx',
        'frontend/src/pages/TestConsole.tsx',
    ]:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if "from '../domain/confirmations'" not in content and 'from "../domain/confirmations"' not in content:
            errors.append(f"{filepath} does not import confirmations.ts")

    # 4. Capability.tsx 必须使用 CONFIRM_LABELS.confirm_quota
    with open('frontend/src/pages/Capability.tsx', 'r', encoding='utf-8') as f:
        cap_content = f.read()
    if 'CONFIRM_LABELS.confirm_quota' not in cap_content:
        errors.append("Capability.tsx does not use CONFIRM_LABELS.confirm_quota")

    # 5. 不允许在 Capability/InvokePanel/TestConsole 中有本地 getRequiredConfirmations 定义（不带 import）
    for filepath in [
        'frontend/src/pages/Capability.tsx',
        'frontend/src/components/InvokePanel.tsx',
        'frontend/src/pages/TestConsole.tsx',
    ]:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # 检查是否有本地定义的 getRequiredConfirmations 且没有 import
        has_local_def = bool(re.search(r'function\s+getRequiredConfirmations\s*\(', content))
        has_import = "from '../domain/confirmations'" in content or 'from "../domain/confirmations"' in content
        if has_local_def and not has_import:
            errors.append(f"{filepath} has local getRequiredConfirmations without import")

    if errors:
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] quota_sensitive confirmation UI implemented correctly")
        return 0

if __name__ == '__main__':
    sys.exit(main())
