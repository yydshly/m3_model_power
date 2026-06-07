#!/usr/bin/env python3
"""检查 Overview.tsx 和 App.tsx 的模型状态文案是否符合 P0 要求。"""
import re
import sys

def main():
    errors = []
    warnings = []

    # 检查 Overview.tsx
    with open('frontend/src/pages/Overview.tsx', 'r', encoding='utf-8') as f:
        overview_content = f.read()

    # 不允许出现的文案
    forbidden_overview = [
        '支持 MiniMax 全系模型',
        '月度约 12 亿',
        '实际可用',
        '未 live 验收',
    ]
    for phrase in forbidden_overview:
        if phrase in overview_content:
            errors.append(f"Overview.tsx 仍包含禁止文案：'{phrase}'")

    # 必须包含的文案
    required_overview = [
        'Chat live 可用',
        '前端启用模型',
        '全量配置',
        'capability_probe 待探测',
        '历史/废弃',
        '当前工作台记录',
    ]
    for phrase in required_overview:
        if phrase not in overview_content:
            errors.append(f"Overview.tsx 缺少必要文案：'{phrase}'")

    # 检查 App.tsx
    with open('frontend/src/App.tsx', 'r', encoding='utf-8') as f:
        app_content = f.read()

    if '能力配置' not in app_content:
        errors.append("App.tsx 缺少 '能力配置' 文案")
    if '启用模型' not in app_content:
        errors.append("App.tsx 缺少 '启用模型' 文案")

    if errors:
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] Overview and App copy aligned correctly")
        return 0

if __name__ == '__main__':
    sys.exit(main())
