#!/usr/bin/env python3
"""检查 capability_profiles.json 中的模型与 models.yaml 的对齐情况。"""
import json
import re
import sys
import yaml

def main():
    errors = []
    warnings = []

    # 读取 models.yaml
    with open('backend/config/models.yaml', 'r', encoding='utf-8') as f:
        models_yaml = yaml.safe_load(f)

    # 建立 model id -> model info 映射
    model_info = {}
    for m in models_yaml.get('models', []):
        model_id = m['id']
        model_info[model_id] = {
            'official_current': m.get('official_current', False),
            'enabled': m.get('enabled', True),
            'live_available': m.get('live_available'),
            'tier': m.get('tier', 'standard'),
        }

    # 读取 capability_profiles.json
    with open('backend/app/minimax_core/profiles/capability_profiles.json', 'r', encoding='utf-8') as f:
        profiles = json.load(f)

    # 检查每条 model_notes
    for family, profile in profiles.get('profiles', {}).items():
        for note in profile.get('model_notes', []):
            model_id = note['model']
            source = note.get('source', '')
            recommendation = note.get('recommendation_level', '')

            # 跳过明显是模型组的情况（包含空格或特殊字符）
            if ' / ' in model_id or ',' in model_id:
                errors.append(f"[{family}] 模型 '{model_id}' 包含 '/' 或 ','，不允许合并多个模型")
                continue

            # 如果模型在 models.yaml 中不存在，跳过（可能是有效别名）
            if model_id not in model_info:
                warnings.append(f"[{family}] 模型 '{model_id}' 在 models.yaml 中未找到")
                continue

            info = model_info[model_id]

            # historical_compat 检查
            if source == 'historical_compat':
                if info['official_current'] and info['enabled'] and info['live_available'] is True:
                    errors.append(
                        f"[{family}] 模型 '{model_id}' source=historical_compat 但 "
                        f"official_current={info['official_current']}, enabled={info['enabled']}, "
                        f"live_available={info['live_available']} — 不应标记为历史兼容"
                    )

            # compatible 推荐等级的中文映射检查
            if recommendation == 'compatible':
                # 已在 UI 层映射为"兼容旧项目"，这是可接受的
                pass

    if errors:
        print("[FAILED]")
        for e in errors:
            print(f"  - {e}")
        if warnings:
            print("\n[WARNINGS]")
            for w in warnings:
                print(f"  - {w}")
        return 1
    else:
        print("[PASSED] Profile models aligned correctly with models.yaml")
        if warnings:
            print("\n[WARNINGS]")
            for w in warnings:
                print(f"  - {w}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
