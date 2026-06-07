#!/usr/bin/env python3
"""检查官方文档对齐漂移：协议、多模态、thinking、context、highspeed 等。"""
import json
import sys
import yaml

def main():
    errors = []
    warnings = []

    # 读取 models.yaml
    with open('backend/config/models.yaml', 'r', encoding='utf-8') as f:
        models_yaml = yaml.safe_load(f)

    # 读取 official_docs_snapshot.json
    with open('backend/app/minimax_core/official_docs/official_docs_snapshot.json', 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    # 建立 model id -> model info 映射
    model_info = {}
    for m in models_yaml.get('models', []):
        model_info[m['id']] = {
            'protocols': m.get('protocols', []),
            'input_modalities': m.get('input_modalities', []),
            'supports_thinking': m.get('supports_thinking'),
            'thinking_can_disable': m.get('thinking_can_disable'),
            'context': m.get('context'),
            'tier': m.get('tier'),
            'cost_level': m.get('cost_level'),
            'quota_eligible': m.get('quota_eligible'),
            'official_current': m.get('official_current'),
            'enabled': m.get('enabled'),
            'live_available': m.get('live_available'),
            'family': m.get('family'),
        }

    # 1. 检查 Anthropic 协议
    anthropic_models = snapshot['sources']['text_anthropic']['supported_models']
    for model_id in anthropic_models:
        if model_id in model_info:
            if 'anthropic' not in model_info[model_id]['protocols']:
                errors.append(f"[PROTOCOL] {model_id}: anthropic not in protocols ({model_info[model_id]['protocols']})")

    # 2. 检查 OpenAI 协议
    openai_models = snapshot['sources']['text_openai']['supported_models']
    for model_id in openai_models:
        if model_id in model_info:
            if 'openai' not in model_info[model_id]['protocols']:
                errors.append(f"[PROTOCOL] {model_id}: openai not in protocols ({model_info[model_id]['protocols']})")

    # 3. 检查多模态（仅 M3 支持 image/video）
    # 只检查 MiniMax-M 系列的 M2.x，不检查 Hailuo 视频模型
    for model_id, info in model_info.items():
        if not model_id.startswith('MiniMax-M'):
            continue
        if model_id == 'MiniMax-M3':
            continue
        mods = info.get('input_modalities', [])
        has_multimodal = 'image' in mods or 'video' in mods
        if has_multimodal:
            errors.append(f"[MODALITY] {model_id}: M2.x should not support image/video ({mods})")

    # 4. 检查 thinking
    for model_id, info in model_info.items():
        if model_id.startswith('MiniMax-M'):
            if model_id == 'MiniMax-M3':
                if not info.get('thinking_can_disable'):
                    errors.append(f"[THINKING] {model_id}: M3 should have thinking_can_disable=true")
            else:
                if info.get('thinking_can_disable'):
                    errors.append(f"[THINKING] {model_id}: M2.x should have thinking_can_disable=false")

    # 5. 检查 context
    expected_context = {
        'MiniMax-M3': 1000000,
    }
    for model_id, expected_ctx in expected_context.items():
        if model_id in model_info:
            actual_ctx = model_info[model_id].get('context')
            if actual_ctx != expected_ctx:
                errors.append(f"[CONTEXT] {model_id}: expected {expected_ctx}, got {actual_ctx}")

    # 6. 检查 highspeed cost_level（仅限 chat family；视频 highspeed 不适用 quota 规则）
    for model_id, info in model_info.items():
        if info.get('family') == 'chat' and info.get('tier') == 'highspeed':
            if info.get('cost_level') != 'quota':
                errors.append(f"[COST] {model_id}: chat highspeed tier should have cost_level=quota, got {info.get('cost_level')}")

    # 7. 检查 profile 中没有合并模型字符串
    with open('backend/app/minimax_core/profiles/capability_profiles.json', 'r', encoding='utf-8') as f:
        profiles = json.load(f)

    for family, profile in profiles.get('profiles', {}).items():
        for note in profile.get('model_notes', []):
            model_id = note.get('model', '')
            if model_id == 'N/A':
                continue  # 非模型条目（如 assets family）
            if '/' in model_id or ',' in model_id:
                errors.append(f"[PROFILE] [{family}] merged model string: '{model_id}'")
            if note.get('source') == 'historical_compat' and model_id in model_info:
                info = model_info[model_id]
                if info.get('official_current') is True and info.get('enabled') is True:
                    errors.append(f"[PROFILE] [{family}] {model_id}: source=historical_compat but official_current=true, enabled=true")

    if errors:
        print(f"[FAILED] {len(errors)} errors found:")
        for e in errors:
            print(f"  - {e}")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)} warnings:")
            for w in warnings:
                print(f"  - {w}")
        return 1
    else:
        print("[PASSED] No drift found in official docs alignment")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)} warnings:")
            for w in warnings:
                print(f"  - {w}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
