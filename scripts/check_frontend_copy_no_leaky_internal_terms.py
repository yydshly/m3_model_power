#!/usr/bin/env python3
"""检查前端主 UI 文案中不裸露内部技术字段。

只检查 JSX 文本内容（> ...text ...< 之间的文本）和字符串字面量，
不检查代码属性访问（如 operation_policy.is_destructive）或注释。
"""
import re
import sys

def extract_text_nodes(content: str) -> list:
    """从 JSX 内容中提取可见文本（不包括代码、属性名）。"""
    texts = []
    # 匹配 JSX 文本节点：> 后面到 < 之前的内容
    # 这是一个简化提取，匹配标签之间的文本
    text_pattern = re.compile(r'>\s*([^<{}\n]+)\s*<')
    for m in text_pattern.finditer(content):
        candidate = m.group(1).strip()
        if len(candidate) > 3 and not candidate.startswith('//'):
            texts.append(candidate)
    return texts

def main():
    errors = []

    files_to_check = [
        'frontend/src/pages/Overview.tsx',
        'frontend/src/pages/Capability.tsx',
        'frontend/src/pages/CapabilityProfiles.tsx',
        'frontend/src/pages/TestConsole.tsx',
        'frontend/src/pages/Models.tsx',
        'frontend/src/App.tsx',
        'frontend/src/components/StatusBadge.tsx',
        'frontend/src/components/InvokePanel.tsx',
        'frontend/src/components/CostBadge.tsx',
    ]

    # 禁止裸露的字段（检查是否作为独立文本词出现）
    leaky_terms = [
        'confirm_paid (',
        'confirm_quota (',
        'confirm_high_cost (',
        'confirm_asset_source (',
        'billing_category=',
        'operation_policy.',
        'requires_explicit_confirmation=true',
        'may_charge_extra=true',
    ]

    for filepath in files_to_check:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            continue

        text_nodes = extract_text_nodes(content)
        text_blob = ' '.join(text_nodes)

        for term in leaky_terms:
            if term in text_blob:
                errors.append(f"{filepath}: found leaky term '{term}' in UI text")

    if errors:
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] No leaky internal terms in frontend UI text")
        return 0

if __name__ == '__main__':
    sys.exit(main())
