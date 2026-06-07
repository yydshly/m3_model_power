#!/usr/bin/env python3
"""检查 TestConsole.tsx 的 UX 文案是否符合 P0 要求。"""
import re
import sys

def main():
    errors = []
    warnings = []

    with open('frontend/src/pages/TestConsole.tsx', 'r', encoding='utf-8') as f:
        content = f.read()

    # 必须包含的文案
    required = [
        '开发者测试控制台',
        '安全检查',
        '真实调用',
        '能力 ID',
        '能力名称',
        '计费/额度',
        '操作风险',
        '普通体验请使用',
        '最近调用记录',
        '重置为示例 payload',
        '复制 payload',
    ]
    for phrase in required:
        if phrase not in content:
            errors.append(f"TestConsole.tsx missing required text: '{phrase}'")

    # 检查调用历史 section header 是否在能力表之后
    # 找到最后一个 <table 的位置（能力表）
    last_table_pos = content.rfind('<table')
    # 找到 "最近调用记录" 作为 section h3 标题（而不是 banner 中的引用）
    # 匹配格式：<h3 ...>最近调用记录
    section_header_match = re.search(r'<h3[^>]*>\s*最近调用记录', content)
    if section_header_match:
        history_section_pos = section_header_match.start()
        if last_table_pos != -1 and history_section_pos < last_table_pos:
            errors.append("'最近调用记录' section appears before capability table - should be after")
    else:
        errors.append("'最近调用记录' section header not found")

    # 检查禁止的独立英文词作为表头
    # 查找 <th>标签中的英文
    th_labels = re.findall(r'<th[^>]*>([A-Za-z ]+)</th>', content)
    forbidden_headers = ['Name', 'Category', 'Scope', 'Billing', 'Risk', 'Verified', 'Desc', 'Actions']
    for th in th_labels:
        for forbidden in forbidden_headers:
            if th.strip() == forbidden:
                errors.append(f"TestConsole.tsx table header still contains English: '{th.strip()}'")

    if errors:
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] TestConsole.tsx UX copy meets requirements")
        if warnings:
            print("\n[WARNINGS]")
            for w in warnings:
                print(f"  - {w}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
