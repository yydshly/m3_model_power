#!/usr/bin/env python3
"""检查模型配额标注与协议 UI 的一致性。

检查项：
1. ChatPanel.tsx 不包含旧计费文案
2. InvokePanel.tsx 不包含旧计费文案
3. 前端包含新计费文案
4. chat highspeed 模型 quota_eligible=true（通过 loader 推导）
5. video highspeed 模型不强制 cost_level=quota
6. MiniMax-Hailuo-2.3-Fast 不被误标为 Token Plan 极速额度
"""
import os
import re
import sys
import yaml


def check_no_old_billing_text(path: str, errors: list[str]) -> None:
    """检查文件不包含旧计费文案。"""
    if not os.path.exists(path):
        errors.append(f"[UI] File not found: {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    old_patterns = [r'\$另计费', r'另计费', r'✓配额']
    for pat in old_patterns:
        if re.search(pat, content):
            errors.append(f"[UI] {path}: contains old billing text pattern '{pat}'")


def check_has_new_billing_text(path: str, errors: list[str], warnings: list[str]) -> None:
    """检查文件使用 quotaLabel 函数来渲染计费文案。"""
    if not os.path.exists(path):
        errors.append(f"[UI] File not found: {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 检查 quotaLabel 函数被导入并使用
    if 'quotaLabel' not in content:
        errors.append(f"[UI] {path}: missing quotaLabel import/usage")
    # 检查没有直接写死的旧文案
    old_patterns = [r'\$另计费', r'另计费', r'✓配额']
    for pat in old_patterns:
        if re.search(pat, content):
            errors.append(f"[UI] {path}: contains old billing text pattern '{pat}'")


def check_chat_highspeed_quota_eligible(models_yaml: dict, errors: list[str]) -> None:
    """检查 chat highspeed 模型的 quota_eligible 推导正确。

    loader.py 推导逻辑：family=chat + cost_level=quota → quota_eligible=true。
    所以 YAML 中 cost_level=quota 的 chat highspeed 模型，在运行时就会得到 quota_eligible=true。
    这里只需验证 cost_level=quota 即可（loader 会自动补全 quota_eligible）。
    """
    for m in models_yaml.get('models', []):
        if m.get('family') == 'chat' and m.get('tier') == 'highspeed':
            cost_level = m.get('cost_level')
            if cost_level != 'quota':
                errors.append(
                    f"[MODEL] {m['id']}: chat+highspeed must have cost_level=quota "
                    f"(loader derives quota_eligible=true), got cost_level={cost_level}"
                )


def check_video_highspeed_not_forced_quota(models_yaml: dict, errors: list[str]) -> None:
    """检查 video highspeed 模型不强制 cost_level=quota。"""
    for m in models_yaml.get('models', []):
        if m.get('family') == 'video' and m.get('tier') == 'highspeed':
            cost_level = m.get('cost_level')
            if cost_level == 'quota':
                errors.append(
                    f"[MODEL] {m['id']}: video highspeed must not have cost_level=quota "
                    f"(视频 highspeed 不适用 chat quota 规则)"
                )


def check_hailuo_23_fast_not_quota(models_yaml: dict, errors: list[str]) -> None:
    """检查 MiniMax-Hailuo-2.3-Fast 不被误标为 Token Plan 极速额度。"""
    for m in models_yaml.get('models', []):
        if m.get('id') == 'MiniMax-Hailuo-2.3-Fast':
            cost_level = m.get('cost_level')
            quota_eligible = m.get('quota_eligible')
            if cost_level == 'quota':
                errors.append(
                    f"[MODEL] MiniMax-Hailuo-2.3-Fast: cost_level must not be 'quota', "
                    f"got '{cost_level}' (视频模型按量计费，不走 Token Plan 极速额度)"
                )
            if quota_eligible is True:
                errors.append(
                    f"[MODEL] MiniMax-Hailuo-2.3-Fast: quota_eligible must not be True, "
                    f"got {quota_eligible}"
                )


def main():
    errors = []
    warnings = []

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. UI 旧文案检查
    chatpanel_path = os.path.join(base, 'frontend', 'src', 'components', 'ChatPanel.tsx')
    invokepanel_path = os.path.join(base, 'frontend', 'src', 'components', 'InvokePanel.tsx')

    check_no_old_billing_text(chatpanel_path, errors)
    check_no_old_billing_text(invokepanel_path, errors)

    # 2. UI 新文案存在性检查
    check_has_new_billing_text(chatpanel_path, errors, warnings)
    check_has_new_billing_text(invokepanel_path, errors, warnings)

    # 3. models.yaml 一致性检查
    models_yaml_path = os.path.join(base, 'backend', 'config', 'models.yaml')
    with open(models_yaml_path, 'r', encoding='utf-8') as f:
        models_yaml = yaml.safe_load(f)

    check_chat_highspeed_quota_eligible(models_yaml, errors)
    check_video_highspeed_not_forced_quota(models_yaml, errors)
    check_hailuo_23_fast_not_quota(models_yaml, errors)

    # 4. loader.py 推导逻辑存在性检查
    loader_path = os.path.join(base, 'backend', 'app', 'minimax_core', 'registry', 'loader.py')
    if os.path.exists(loader_path):
        with open(loader_path, 'r', encoding='utf-8') as f:
            loader_content = f.read()
        # 验证 loader 包含推导逻辑
        if 'quota_eligible' not in loader_content or 'family' not in loader_content:
            warnings.append(
                "[LOADER] loader.py may be missing quota_eligible derivation logic"
            )
    else:
        errors.append(f"[LOADER] loader.py not found: {loader_path}")

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
        print("[PASSED] UI and quota consistency checks passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
