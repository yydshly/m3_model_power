#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产品化工作台完成报告文档检查。

检查项：
1. docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md 存在
2. 报告中必须出现 PR #10 / PR #11 / PR #12
3. 报告中必须出现 Invocation history / UsageCostExplainer / Overview
4. 报告中必须出现 RiskGate
5. 报告中必须出现 warning_only / out_of_scope
6. README.md 必须链接 PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md
7. README.md 不得出现"下次续费"
8. README.md 不得把本项目称为 MiniMax 官方套餐说明
9. 如存在 docs/README.md，必须链接 PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md
"""
import os
import re
import sys


def _base():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_completion_report_exists(errors, warnings):
    base = _base()
    path = os.path.join(base, "docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md")
    if not os.path.exists(path):
        errors.append("[DOCS] docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md not found")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if len(content) < 500:
        errors.append("[DOCS] PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md seems incomplete (< 500 chars)")


def check_report_mentions_prs(errors, warnings):
    base = _base()
    path = os.path.join(base, "docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md")
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as f:
        content_lower = f.read().lower()
    required_prs = [('pr #10', 'PR #10'), ('pr #11', 'PR #11'), ('pr #12', 'PR #12')]
    for pr_lower, pr in required_prs:
        if pr_lower not in content_lower:
            errors.append(f"[DOCS] Report missing mention of {pr}")


def check_report_mentions_key_features(errors, warnings):
    base = _base()
    path = os.path.join(base, "docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md")
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as f:
        content_lower = f.read().lower()
    required_features = [
        ('invocation history', 'Invocation history'),
        ('usagecostexplainer', 'UsageCostExplainer'),
        ('overview', 'Overview'),
    ]
    for feature_lower, label in required_features:
        if feature_lower not in content_lower:
            errors.append(f"[DOCS] Report missing mention of {label}")


def check_report_mentions_riskgate(errors, warnings):
    base = _base()
    path = os.path.join(base, "docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md")
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as f:
        content_lower = f.read().lower()
    if 'riskgate' not in content_lower:
        errors.append("[DOCS] Report missing mention of RiskGate")


def check_report_mentions_scope_types(errors, warnings):
    base = _base()
    path = os.path.join(base, "docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md")
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as f:
        content_lower = f.read().lower()
    required = [('warning_only', 'warning_only'), ('out_of_scope', 'out_of_scope')]
    for scope_lower, scope in required:
        if scope_lower not in content_lower:
            errors.append(f"[DOCS] Report missing mention of '{scope}'")


def check_readme_links_completion_report(errors, warnings):
    base = _base()
    readme = os.path.join(base, "README.md")
    if not os.path.exists(readme):
        errors.append("[README] README.md not found")
        return
    with open(readme, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'PRODUCTIZED_WORKBENCH_COMPLETION_REPORT' not in content:
        errors.append("[README] README.md does not link to PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md")


def check_readme_no_renewal_copy(errors, warnings):
    base = _base()
    readme = os.path.join(base, "README.md")
    if not os.path.exists(readme):
        return
    with open(readme, 'r', encoding='utf-8') as f:
        content = f.read()
    if re.search(r'下次续费', content):
        errors.append("[README] README.md contains '下次续费' (personal billing info should not appear)")


def check_readme_not_official_plan_description(errors, warnings):
    base = _base()
    readme = os.path.join(base, "README.md")
    if not os.path.exists(readme):
        return
    with open(readme, 'r', encoding='utf-8') as f:
        content = f.read()
    # Check for language that claims this is an official MiniMax plan description
    bad_patterns = [
        (r'官方.*套餐.*说明', 'official plan description'),
        (r'MiniMax\s+官方\s+套餐', 'MiniMax official plan'),
    ]
    for pattern, label in bad_patterns:
        if re.search(pattern, content):
            errors.append(f"[README] README.md contains '{label}' language")


def check_docs_readme_links_completion_report(errors, warnings):
    base = _base()
    docs_readme = os.path.join(base, "docs/README.md")
    if not os.path.exists(docs_readme):
        # docs/README.md is optional
        return
    with open(docs_readme, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'PRODUCTIZED_WORKBENCH_COMPLETION_REPORT' not in content:
        errors.append("[DOCS] docs/README.md does not link to PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md")


def main():
    errors = []
    warnings = []

    check_completion_report_exists(errors, warnings)
    check_report_mentions_prs(errors, warnings)
    check_report_mentions_key_features(errors, warnings)
    check_report_mentions_riskgate(errors, warnings)
    check_report_mentions_scope_types(errors, warnings)
    check_readme_links_completion_report(errors, warnings)
    check_readme_no_renewal_copy(errors, warnings)
    check_readme_not_official_plan_description(errors, warnings)
    check_docs_readme_links_completion_report(errors, warnings)

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
        print("[PASSED] Productized workbench documentation check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
