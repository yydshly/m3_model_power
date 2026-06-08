#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check Overview.tsx and App.tsx model status copy against P0 requirements."""
import os
import sys


def _base():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _all_overview_files():
    base = _base()
    dirs = [
        os.path.join(base, "frontend/src/pages"),
        os.path.join(base, "frontend/src/components/overview"),
        os.path.join(base, "frontend/src/domain"),
    ]
    files = []
    for d in dirs:
        if os.path.exists(d):
            for root, _, fnames in os.walk(d):
                for f in fnames:
                    if f.endswith(('.ts', '.tsx')):
                        files.append(os.path.join(root, f))
    return files


def main():
    errors = []
    warnings = []

    base = _base()
    overview_page = os.path.join(base, "frontend/src/pages/Overview.tsx")

    # Forbidden strings — must NOT appear in main Overview.tsx
    with open(overview_page, 'r', encoding='utf-8') as f:
        overview_content = f.read()

    forbidden_overview = [
        '支持 MiniMax 全系模型',
        '月度约 12 亿',
        '实际可用',
        '未 live 验收',
    ]
    for phrase in forbidden_overview:
        if phrase in overview_content:
            errors.append(f"Overview.tsx still contains forbidden copy: '{phrase}'")

    # Required strings — check across all overview component files (diagnostics section)
    all_content_parts = []
    for fpath in _all_overview_files():
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                all_content_parts.append(f.read())
        except Exception:
            pass
    all_content = '\n'.join(all_content_parts)

    # These model diagnostic labels should exist in the diagnostics section
    required_diagnostic_labels = [
        'Chat live 可用',
        '前端启用模型',
        '全量配置',
        'capability_probe 待探测',
        '历史/废弃',
    ]
    for phrase in required_diagnostic_labels:
        if phrase not in all_content:
            errors.append(f"Required diagnostic label '{phrase}' not found in overview components")

    # The old title "当前工作台记录" was replaced with new hero section
    # No longer required as a specific title string

    # App.tsx checks
    app_path = os.path.join(base, "frontend/src/App.tsx")
    with open(app_path, 'r', encoding='utf-8') as f:
        app_content = f.read()

    if '能力配置' not in app_content:
        errors.append("App.tsx missing '能力配置' copy")
    if '启用模型' not in app_content:
        errors.append("App.tsx missing '启用模型' copy")

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
