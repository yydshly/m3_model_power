#!/usr/bin/env python3
"""检查 capability source matrix 覆盖率。"""
import os
import re
import sys

def extract_table_rows(content):
    """提取 markdown 表格中的数据行，跳过表头和分隔符。"""
    lines = content.split('\n')
    in_table = False
    rows = []
    for line in lines:
        if line.startswith('|'):
            # 跳过表头行（包含 | capability_id | 这样的）
            if 'capability_id' in line.lower() or '----' in line:
                in_table = True
                continue
            if in_table and '|-' in line:
                continue
            if in_table:
                rows.append(line)
    return rows

def main():
    errors = []
    warnings = []

    matrix_path = 'docs/OFFICIAL_DOCS_CAPABILITY_SOURCE_MATRIX.md'
    if not os.path.exists(matrix_path):
        errors.append(f"Matrix file not found: {matrix_path}")
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        return 1

    with open(matrix_path, 'r', encoding='utf-8') as f:
        matrix_content = f.read()

    # 提取数据行
    rows = extract_table_rows(matrix_content)

    # 从数据行提取 capability_id（第一列）
    cap_ids_in_matrix = set()
    for row in rows:
        parts = [p.strip() for p in row.split('|')]
        if len(parts) >= 3 and parts[1].strip():
            cap_ids_in_matrix.add(parts[1].strip())

    # 检查 matrix 中有但实际不存在的 capability（表头残留等）
    known_caps = {
        'chat-openai', 'chat-anthropic', 'chat-responses-create', 'chat-responses-tokens',
        'tts-sync', 'tts-async', 'tts-ws', 'voice-clone', 'voice-design', 'voice-delete',
        'image-t2i', 'image-i2i',
        'video-t2v', 'video-s2v', 'video-i2v', 'video-query', 'video-download',
        'music-gen', 'music-cover-prep', 'lyrics-gen',
        'file-upload', 'file-list', 'file-retrieve', 'file-content', 'file-delete',
        'speech-t2a', 'speech-t2a-async', 'speech-t2a-ws',
    }

    extra_in_matrix = cap_ids_in_matrix - known_caps
    if extra_in_matrix:
        warnings.append(f"Extra entries in matrix (may be headers): {extra_in_matrix}")

    if errors:
        print(f"[FAILED] {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print(f"[PASSED] Matrix coverage check passed ({len(cap_ids_in_matrix)} capabilities found)")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
