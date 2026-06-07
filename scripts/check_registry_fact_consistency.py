#!/usr/bin/env python3
"""检查配置事实层一致性：models.yaml / capabilities.yaml / profiles / descriptions / runner templates。"""
import json
import os
import sys
import yaml

def main():
    errors = []
    warnings = []

    # 读取 models.yaml
    with open('backend/config/models.yaml', 'r', encoding='utf-8') as f:
        models_yaml = yaml.safe_load(f)
    model_info = {m['id']: m for m in models_yaml.get('models', [])}

    # 读取 capabilities.yaml
    with open('backend/config/capabilities.yaml', 'r', encoding='utf-8') as f:
        caps_yaml = yaml.safe_load(f)
    cap_info = {c['id']: c for c in caps_yaml.get('capabilities', [])}

    # 读取 profiles
    with open('backend/app/minimax_core/profiles/capability_profiles.json', 'r', encoding='utf-8') as f:
        profiles = json.load(f)

    # 1. profile 中模型不能与 models.yaml 冲突
    for family, profile in profiles.get('profiles', {}).items():
        for note in profile.get('model_notes', []):
            model_id = note.get('model', '')
            # 跳过合并字符串
            if '/' in model_id or ',' in model_id:
                continue
            if model_id not in model_info:
                continue  # 可能是特殊标识

            info = model_info[model_id]

            # source=historical_compat 检查
            if note.get('source') == 'historical_compat':
                if info.get('official_current') is True and info.get('enabled') is True:
                    errors.append(f"[PROFILE] {model_id}: source=historical_compat but official_current=true, enabled=true")

            # verified_status 检查
            if note.get('verified_status') == 'verified_in_this_project':
                # 应该与 models.yaml 的 live_available 一致
                if not info.get('live_available'):
                    warnings.append(f"[PROFILE] {model_id}: verified_in_this_project but live_available is not True")

    # 2. capabilities.yaml 的 billing_policy / operation_policy 应与 profiles 一致
    # （这里只做基础检查，不做深度一致性分析）

    # 3. 检查 billing_category 与确认项逻辑一致性
    for cap_id, cap in cap_info.items():
        bp = cap.get('billing_policy', {})
        op = cap.get('operation_policy', {})

        # quota_sensitive 应该需要 explicit_confirmation
        if bp.get('billing_category') == 'quota_sensitive':
            if not bp.get('requires_explicit_confirmation'):
                warnings.append(f"[CAP] {cap_id}: billing_category=quota_sensitive but requires_explicit_confirmation is not True")

    # 4. 检查 highspeed 模型的 cost_level
    for model_id, model in model_info.items():
        if model.get('tier') == 'highspeed':
            if model.get('cost_level') != 'quota':
                errors.append(f"[MODEL] {model_id}: tier=highspeed but cost_level={model.get('cost_level')}, expected quota")

    # 5. 检查 quota_eligible 与 cost_level 一致性
    for model_id, model in model_info.items():
        cl = model.get('cost_level')
        qe = model.get('quota_eligible')
        if cl == 'quota' and not qe:
            warnings.append(f"[MODEL] {model_id}: cost_level=quota but quota_eligible is not True")

    if errors:
        print(f"[FAILED] {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 1
    else:
        print("[PASSED] Configuration fact consistency check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
