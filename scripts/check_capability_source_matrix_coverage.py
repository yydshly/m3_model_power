#!/usr/bin/env python3
"""检查 capability source matrix 覆盖率。

读取 backend/config/capabilities.yaml 中的全部 capability id，
与 docs/OFFICIAL_DOCS_CAPABILITY_SOURCE_MATRIX.md 中的覆盖情况进行对比，
缺失项直接失败，不允许只 warning。
"""
import os
import sys
import yaml


def extract_capability_ids(content):
    """从 matrix 文件中提取 capability_id。

    matrix 格式是非标准的：capability_id 作为表头列名，
    实际 ID 值在 capability_id 列下单独成行，形如：
      | capability_id | chat-openai |

    跳过 ## Schema 章节（它是说明性表格，不是真实 capability 条目）。
    """
    ids = []
    in_schema = False
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped == '## Schema':
            in_schema = True
            continue
        if stripped.startswith('## '):
            in_schema = False
            continue
        if in_schema:
            continue
        if not stripped.startswith('|'):
            continue
        parts = [p.strip() for p in stripped.split('|')]
        # 格式: | capability_id | <id> |
        if len(parts) >= 3 and parts[1] == 'capability_id' and parts[2].strip():
            ids.append(parts[2].strip())
    return ids


def main():
    errors = []

    caps_yaml_path = 'backend/config/capabilities.yaml'
    if not os.path.exists(caps_yaml_path):
        errors.append(f"Capabilities file not found: {caps_yaml_path}")
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1

    matrix_path = 'docs/OFFICIAL_DOCS_CAPABILITY_SOURCE_MATRIX.md'
    if not os.path.exists(matrix_path):
        errors.append(f"Matrix file not found: {matrix_path}")
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1

    # 1. 读取 capabilities.yaml 获取全部 capability id
    with open(caps_yaml_path, 'r', encoding='utf-8') as f:
        caps_doc = yaml.safe_load(f)

    configured_caps = {cap['id'] for cap in caps_doc.get('capabilities', [])}
    configured_total = len(configured_caps)

    # 2. 读取 matrix 获取覆盖的 capability id
    with open(matrix_path, 'r', encoding='utf-8') as f:
        matrix_content = f.read()

    cap_ids_in_matrix = set(extract_capability_ids(matrix_content))
    matrix_covered = len(cap_ids_in_matrix)

    # 3. 计算差异
    missing_ids = configured_caps - cap_ids_in_matrix
    extra_ids = cap_ids_in_matrix - configured_caps

    if missing_ids:
        errors.append(f"Missing in matrix ({len(missing_ids)}): {sorted(missing_ids)}")
    if extra_ids:
        errors.append(f"Extra in matrix but not in capabilities.yaml ({len(extra_ids)}): {sorted(extra_ids)}")

    # 输出统计
    print(f"configured_total: {configured_total}")
    print(f"matrix_covered:   {matrix_covered}")
    print(f"missing_ids:     {sorted(missing_ids)}")
    print(f"extra_ids:       {sorted(extra_ids)}")

    if errors:
        print(f"\n[FAILED] {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("\n[PASSED] Matrix coverage check passed — all capabilities documented")
        return 0


if __name__ == '__main__':
    sys.exit(main())
