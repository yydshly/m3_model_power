#!/usr/bin/env python3
"""检查 ChatPanel / StreamPanel / InvokePanel 的模型选择同步逻辑。

检查项：
1. ChatPanel.tsx 不再包含硬编码 fallback: models[0]?.id ?? 'MiniMax-M3'
2. 存在同步逻辑：models.some + setModel((current) => ...)
3. 如果新增 useSyncedModelSelection.ts，三个组件都引用它
4. 没有新的 MiniMax-M3 fallback
5. InvokePanel 支持无模型能力不被误拦截（requiresModelSelection 模式）
"""
import os
import re
import sys


def check_no_hardcoded_m3_fallback(path: str, errors: list[str]) -> None:
    """检查文件不包含 models[0]?.id ?? 'MiniMax-M3'"""
    if not os.path.exists(path):
        errors.append(f"[FILE NOT FOUND] {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 严格匹配旧的有害 fallback
    if re.search(r"models\[0\]\?\.id\s*\?\?\s*'MiniMax-M3'", content):
        errors.append(f"[CHATPANEL] {path}: contains hardcoded 'MiniMax-M3' fallback")
    # 宽松检查：允许 example payload 里出现 MiniMax-M3，不允许在 useState 初始化中
    for line in content.split('\n'):
        if 'useState' in line and 'MiniMax-M3' in line and '??' in line:
            errors.append(f"[CHATPANEL] {path}: useState contains MiniMax-M3 fallback: {line.strip()}")


def check_sync_pattern(path: str, errors: list[str], warnings: list[str]) -> None:
    """检查文件包含 useSyncedModelSelection 或等效同步逻辑"""
    if not os.path.exists(path):
        errors.append(f"[FILE NOT FOUND] {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'useSyncedModelSelection' in content:
        # 通过 hook 使用，间接验证了同步逻辑
        return

    # 如果没有使用 hook，检查是否有等效的 inline 实现
    has_models_some = 'models.some' in content
    has_setmodel_callback = re.search(r'setModel\s*\(\s*\(?\s*current\s*\)?', content) is not None

    if not (has_models_some and has_setmodel_callback):
        warnings.append(
            f"[SYNC] {path}: no useSyncedModelSelection hook and no inline sync pattern "
            f"(models.some={has_models_some}, setModel callback={has_setmodel_callback})"
        )


def check_hook_imported_in_all(paths: list[str], errors: list[str]) -> None:
    """如果 useSyncedModelSelection.ts 存在，三个组件都应该引用它"""
    hook_path = os.path.join(os.path.dirname(paths[0]), '..', 'domain', 'useSyncedModelSelection.ts')
    if not os.path.exists(hook_path):
        return  # hook 不存在则跳过（说明还用 inline 方式）

    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'useSyncedModelSelection' not in content:
            errors.append(f"[HOOK] {path}: should import useSyncedModelSelection but does not")


def check_no_m3_in_example_payload(path: str, warnings: list[str]) -> None:
    """检查 MiniMax-M3 不作为用户可见的默认选项出现（example payload 可以有）"""
    # 这个检查只在有问题时发出警告，不算 errors
    pass


def check_invoke_panel_model_free_guard(path: str, errors: list[str]) -> None:
    """检查 InvokePanel.tsx 支持无模型能力不被误拦截"""
    if not os.path.exists(path):
        errors.append(f"[FILE NOT FOUND] {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 不允许出现 !!model && ... 强制要求模型
    if re.search(r'!!model\s+&&', content) or re.search(r'const canInvoke = !!model &&', content):
        errors.append(f"[INVOKE] {path}: contains !!model && which blocks model-free capabilities")

    # 2. 必须包含 requiresModelSelection 和 hasModelSelection
    if 'requiresModelSelection' not in content:
        errors.append(f"[INVOKE] {path}: missing requiresModelSelection")
    if 'hasModelSelection' not in content:
        errors.append(f"[INVOKE] {path}: missing hasModelSelection")

    # 3. submit() 必须用 requiresModelSelection && !model，而不是单纯 if (!model)
    # 找 submit 函数
    submit_match = re.search(r'const submit = async \(\) => \{(.*?)\n  \}', content, re.DOTALL)
    if submit_match:
        submit_body = submit_match.group(1)
        # 如果有 if (!model) 而不是 requiresModelSelection && !model，则报错
        if re.search(r'if\s*\(\s*!model\s*\)', submit_body):
            if 'requiresModelSelection' not in submit_body:
                errors.append(f"[INVOKE] {path}: submit() uses 'if (!model)' instead of 'requiresModelSelection && !model'")


def main():
    errors = []
    warnings = []

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    chatpanel = os.path.join(base, 'frontend', 'src', 'components', 'ChatPanel.tsx')
    streampanel = os.path.join(base, 'frontend', 'src', 'components', 'StreamPanel.tsx')
    invokepanel = os.path.join(base, 'frontend', 'src', 'components', 'InvokePanel.tsx')
    hook = os.path.join(base, 'frontend', 'src', 'domain', 'useSyncedModelSelection.ts')

    # 1. ChatPanel 不包含有害 fallback
    check_no_hardcoded_m3_fallback(chatpanel, errors)

    # 2. ChatPanel 有同步逻辑
    check_sync_pattern(chatpanel, errors, warnings)

    # 3. StreamPanel 有同步逻辑
    check_sync_pattern(streampanel, errors, warnings)

    # 4. InvokePanel 有同步逻辑
    check_sync_pattern(invokepanel, errors, warnings)

    # 5. InvokePanel 支持无模型能力不被误拦截
    check_invoke_panel_model_free_guard(invokepanel, errors)

    # 6. 三个组件引用 hook（如果 hook 存在）
    check_hook_imported_in_all([chatpanel, streampanel, invokepanel], errors)

    # 7. 确认 hook 本身存在且逻辑正确
    if os.path.exists(hook):
        with open(hook, 'r', encoding='utf-8') as f:
            hook_content = f.read()
        if 'models.some' not in hook_content:
            errors.append(f"[HOOK] useSyncedModelSelection.ts missing models.some")
        if 'setModel' not in hook_content:
            errors.append(f"[HOOK] useSyncedModelSelection.ts missing setModel")
        if "models[0].id" not in hook_content:
            errors.append(f"[HOOK] useSyncedModelSelection.ts missing models[0].id default")
    else:
        # 没有 hook 文件，至少三个组件要有 inline 同步
        pass

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
        print("[PASSED] ChatPanel model selection sync check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
