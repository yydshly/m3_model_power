#!/usr/bin/env python3
"""检查确认项逻辑是否统一从 confirmations.ts 引用。"""
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

    # 2. 三个文件必须 import 它
    files_that_should_import = [
        'frontend/src/pages/Capability.tsx',
        'frontend/src/components/InvokePanel.tsx',
        'frontend/src/pages/TestConsole.tsx',
    ]

    for filepath in files_that_should_import:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if "from '../domain/confirmations'" not in content and 'from "../domain/confirmations"' not in content:
            errors.append(f"{filepath} 未 import confirmations.ts")

    # 3. 三个文件中不得有重复定义的 getRequiredConfirmations
    for filepath in files_that_should_import:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有本地定义的 getRequiredConfirmations（不是通过 import）
        # 匹配 function getRequiredConfirmations 或 const getRequiredConfirmations
        local_def_pattern = r'(?:function|const)\s+getRequiredConfirmations\s*[=(]'
        has_local_def = bool(re.search(local_def_pattern, content))

        # 检查是否有 import
        has_import = "from '../domain/confirmations'" in content or 'from "../domain/confirmations"' in content

        if has_local_def and not has_import:
            errors.append(f"{filepath} 存在本地 getRequiredConfirmations 定义且未 import")

    # 4. 不得重复定义 CONFIRM_LABELS
    for filepath in files_that_should_import:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有本地定义的 CONFIRM_LABELS
        local_confirm_labels = re.search(r'const\s+CONFIRM_LABELS\s*:\s*Record<string,\s*string>', content)
        has_import = "from '../domain/confirmations'" in content or 'from "../domain/confirmations"' in content

        if local_confirm_labels and not has_import:
            errors.append(f"{filepath} 存在本地 CONFIRM_LABELS 定义且未 import")

    if errors:
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] Confirmation logic unified from confirmations.ts")
        return 0

if __name__ == '__main__':
    sys.exit(main())
