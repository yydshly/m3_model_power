#!/usr/bin/env python3
"""Check chat protocol Runner closure for P1-3.

Checks:
 1. chat-anthropic in RUNNER_SUPPORTED_CAPABILITIES
 2. chat-responses-create in RUNNER_SUPPORTED_CAPABILITIES
 3.二者不在 ADVANCED_TEST_CAPABILITIES
 4. chat-responses-tokens 仍在 ADVANCED_TEST_CAPABILITIES
 5. backend __init__.py 支持二者
 6. chat-anthropic template 存在
 7. chat-responses-create template 存在
 8. 二者 result_type == "chat"
 9. chat-anthropic payload 使用 messages
10. chat-responses-create payload 使用 input
11. ChatResultPreview.tsx 存在
12. ChatResultPreview 支持 choices[0].message.content
13. ChatResultPreview 支持 content[0].text
14. ChatResultPreview 支持 output_text
15. CapabilityRunner.tsx result_type==="chat" 时使用 ChatResultPreview
16. chat.py 三类 handler 强制非流式
17. audit 文档 A 类包含 chat-anthropic / chat-responses-create
18. audit 文档 B 类保留 chat-responses-tokens
19. ChatResultPreview has getTextBlockText helper
20. ChatResultPreview supports output_text type block
21. ChatResultPreview supports content block without type
22. ChatResultPreview supports nested data.content
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_PATH = _ROOT / "backend" / "app" / "minimax_core" / "runner" / "capability_runner_templates.json"
_CAP_LINKS = _ROOT / "frontend" / "src" / "navigation" / "capabilityLinks.ts"
_RUNNER_INIT = _ROOT / "backend" / "app" / "minimax_core" / "runner" / "__init__.py"
_RUNNER_PAGE = _ROOT / "frontend" / "src" / "pages" / "CapabilityRunner.tsx"
_CHAT_PREVIEW = _ROOT / "frontend" / "src" / "components" / "ChatResultPreview.tsx"
_CHAT_PY = _ROOT / "backend" / "app" / "capabilities" / "chat.py"
_AUDIT_DOC = _ROOT / "docs" / "WORKBENCH_CAPABILITY_CLOSURE_AUDIT.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_templates() -> dict:
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f).get("templates", {})


def parse_set(ts_content: str, set_name: str) -> list[str]:
    """Parse a Set from TypeScript source, stripping single-line comments."""
    stripped = re.sub(r'//.*', '', ts_content)
    match = re.search(rf'{set_name}\s*=\s*new\s+Set\(\s*\[(.*?)\]', stripped, re.DOTALL)
    if not match:
        return []
    return [x.strip().strip("'\"") for x in match.group(1).split(',') if x.strip()]


def check_1_chat_anthropic_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'chat-anthropic' not in caps:
        print("FAIL: chat-anthropic not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: chat-anthropic is in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_2_chat_responses_create_in_runner_supported() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'chat-responses-create' not in caps:
        print("FAIL: chat-responses-create not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: chat-responses-create is in RUNNER_SUPPORTED_CAPABILITIES")
    return True


def check_3_not_in_advanced_test() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'ADVANCED_TEST_CAPABILITIES')
    bad = [c for c in ['chat-anthropic', 'chat-responses-create'] if c in caps]
    if bad:
        print(f"FAIL: {bad} should NOT be in ADVANCED_TEST_CAPABILITIES")
        return False
    print("PASS: chat-anthropic and chat-responses-create are NOT in ADVANCED_TEST_CAPABILITIES")
    return True


def check_4_responses_tokens_still_advanced() -> bool:
    caps = parse_set(read(_CAP_LINKS), 'ADVANCED_TEST_CAPABILITIES')
    if 'chat-responses-tokens' not in caps:
        print("FAIL: chat-responses-tokens should remain in ADVANCED_TEST_CAPABILITIES")
        return False
    print("PASS: chat-responses-tokens remains in ADVANCED_TEST_CAPABILITIES")
    return True


def check_5_backend_supports_both() -> bool:
    content = read(_RUNNER_INIT)
    for cap in ['chat-anthropic', 'chat-responses-create']:
        if cap not in content:
            print(f"FAIL: {cap} not found in runner __init__.py")
            return False
    print("PASS: backend runner __init__.py supports chat-anthropic and chat-responses-create")
    return True


def check_6_chat_anthropic_template_exists() -> bool:
    templates = load_templates()
    if 'chat-anthropic' not in templates:
        print("FAIL: chat-anthropic template missing")
        return False
    print("PASS: chat-anthropic template exists")
    return True


def check_7_chat_responses_create_template_exists() -> bool:
    templates = load_templates()
    if 'chat-responses-create' not in templates:
        print("FAIL: chat-responses-create template missing")
        return False
    print("PASS: chat-responses-create template exists")
    return True


def check_8_both_result_type_chat() -> bool:
    templates = load_templates()
    for cap in ['chat-anthropic', 'chat-responses-create']:
        rt = templates.get(cap, {}).get('result_type', '')
        if rt != 'chat':
            print(f"FAIL: {cap} result_type is '{rt}', expected 'chat'")
            return False
    print("PASS: both chat-anthropic and chat-responses-create have result_type 'chat'")
    return True


def check_9_chat_anthropic_uses_messages() -> bool:
    templates = load_templates()
    payload = templates.get('chat-anthropic', {}).get('payload_template', {})
    if 'messages' not in payload:
        print("FAIL: chat-anthropic payload_template missing 'messages'")
        return False
    print("PASS: chat-anthropic payload_template uses 'messages'")
    return True


def check_10_chat_responses_uses_input() -> bool:
    templates = load_templates()
    payload = templates.get('chat-responses-create', {}).get('payload_template', {})
    if 'input' not in payload:
        print("FAIL: chat-responses-create payload_template missing 'input'")
        return False
    print("PASS: chat-responses-create payload_template uses 'input'")
    return True


def check_11_chat_preview_exists() -> bool:
    if not _CHAT_PREVIEW.exists():
        print(f"FAIL: {_CHAT_PREVIEW} does not exist")
        return False
    print("PASS: ChatResultPreview.tsx exists")
    return True


def check_12_supports_openai_choices() -> bool:
    content = read(_CHAT_PREVIEW)
    if "choices" not in content or "message" not in content or "content" not in content:
        print("FAIL: ChatResultPreview does not reference choices[0].message.content pattern")
        return False
    print("PASS: ChatResultPreview supports OpenAI choices pattern")
    return True


def check_13_supports_anthropic_content() -> bool:
    content = read(_CHAT_PREVIEW)
    if "content" not in content or "type" not in content or "text" not in content:
        print("FAIL: ChatResultPreview does not reference content[0].text pattern")
        return False
    print("PASS: ChatResultPreview supports Anthropic content pattern")
    return True


def check_14_supports_responses_output_text() -> bool:
    content = read(_CHAT_PREVIEW)
    if "output_text" not in content:
        print("FAIL: ChatResultPreview does not reference output_text")
        return False
    print("PASS: ChatResultPreview supports Responses output_text")
    return True


def check_15_runner_uses_chat_preview() -> bool:
    content = read(_RUNNER_PAGE)
    # Must import ChatResultPreview
    if "ChatResultPreview" not in content:
        print("FAIL: CapabilityRunner.tsx does not import ChatResultPreview")
        return False
    # Must render ChatResultPreview for resultType === 'chat'
    if "resultType === 'chat'" not in content and 'resultType === "chat"' not in content:
        print("FAIL: CapabilityRunner.tsx does not check resultType === 'chat'")
        return False
    if "<ChatResultPreview" not in content:
        print("FAIL: CapabilityRunner.tsx does not render <ChatResultPreview>")
        return False
    print("PASS: CapabilityRunner.tsx uses ChatResultPreview for chat result type")
    return True


def check_16_handlers_non_streaming() -> bool:
    content = read(_CHAT_PY)
    # All three must enforce non-streaming
    issues = []
    # chat_anthropic: should pop stream
    if 'stream' not in content or 'pop' not in content:
        issues.append("chat.py does not pop stream")
    # chat_openai: should set stream=False
    if 'stream' not in content or 'False' not in content:
        issues.append("chat.py does not force stream=False")
    if issues:
        for i in issues:
            print(f"FAIL: {i}")
        return False
    print("PASS: chat.py handlers enforce non-streaming (pop stream / stream=False)")
    return True


def check_17_audit_doc_a_class() -> bool:
    content = read(_AUDIT_DOC)
    for cap in ['chat-anthropic', 'chat-responses-create']:
        if cap not in content:
            print(f"FAIL: {cap} not found in audit doc")
            return False
    # Check A-class section
    a_match = re.search(r'### A 类.*?(?=### B 类|#)', content, re.DOTALL)
    if not a_match:
        print("FAIL: A-class section not found in audit doc")
        return False
    a_text = a_match.group()
    for cap in ['chat-anthropic', 'chat-responses-create']:
        if cap not in a_text:
            print(f"FAIL: {cap} not in A-class section of audit doc")
            return False
    print("PASS: audit doc A-class includes chat-anthropic and chat-responses-create")
    return True


def check_18_audit_doc_b_class() -> bool:
    content = read(_AUDIT_DOC)
    # B-class section should have chat-responses-tokens but NOT chat-anthropic or chat-responses-create
    b_match = re.search(r'### B 类.*?(?=### C 类|### A 类|## |\Z)', content, re.DOTALL)
    if not b_match:
        print("FAIL: B-class section not found in audit doc")
        return False
    b_text = b_match.group()
    if 'chat-responses-tokens' not in b_text:
        print("FAIL: chat-responses-tokens not in B-class section of audit doc")
        return False
    for cap in ['chat-anthropic', 'chat-responses-create']:
        if cap in b_text:
            print(f"FAIL: {cap} should NOT be in B-class section of audit doc")
            return False
    print("PASS: audit doc B-class retains chat-responses-tokens (not the new chat Runners)")
    return True


def check_19_has_get_text_block_helper() -> bool:
    content = read(_CHAT_PREVIEW)
    if "getTextBlockText" not in content:
        print("FAIL: ChatResultPreview missing getTextBlockText helper function")
        return False
    print("PASS: ChatResultPreview has getTextBlockText helper")
    return True


def check_20_supports_output_text_type_block() -> bool:
    content = read(_CHAT_PREVIEW)
    # Should handle output type block (type === 'output_text')
    if "'output_text'" not in content and '"output_text"' not in content:
        print("FAIL: ChatResultPreview does not handle output_text type block")
        return False
    # Also check the helper function handles output_text type
    if "type === 'output_text'" not in content and 'type === "output_text"' not in content:
        print("FAIL: getTextBlockText does not handle output_text type")
        return False
    print("PASS: ChatResultPreview supports output_text type block")
    return True


def check_21_supports_bare_content_block() -> bool:
    content = read(_CHAT_PREVIEW)
    # Should handle content blocks without type (bare block)
    if "(!first.type || first.type === 'text')" not in content and \
       '(!first.type || first.type === "text")' not in content:
        print("FAIL: ChatResultPreview does not handle bare content block (no type)")
        return False
    print("PASS: ChatResultPreview supports bare content block without type")
    return True


def check_22_supports_nested_data_content() -> bool:
    content = read(_CHAT_PREVIEW)
    # Should check nested data.content path (via 'nested' alias variable)
    if "nested" not in content or ".content" not in content:
        print("FAIL: ChatResultPreview does not support nested data.content extraction")
        return False
    print("PASS: ChatResultPreview supports nested data.content extraction")
    return True


def main():
    print("=" * 60)
    print("Chat Protocol Runner Closure checks (P1-3)")
    print("=" * 60)

    checks = [
        ("chat-anthropic in RUNNER_SUPPORTED_CAPABILITIES", check_1_chat_anthropic_in_runner_supported),
        ("chat-responses-create in RUNNER_SUPPORTED_CAPABILITIES", check_2_chat_responses_create_in_runner_supported),
        ("NOT in ADVANCED_TEST_CAPABILITIES", check_3_not_in_advanced_test),
        ("chat-responses-tokens still ADVANCED_TEST", check_4_responses_tokens_still_advanced),
        ("backend __init__.py supports both", check_5_backend_supports_both),
        ("chat-anthropic template exists", check_6_chat_anthropic_template_exists),
        ("chat-responses-create template exists", check_7_chat_responses_create_template_exists),
        ("both result_type == 'chat'", check_8_both_result_type_chat),
        ("chat-anthropic uses messages payload", check_9_chat_anthropic_uses_messages),
        ("chat-responses-create uses input payload", check_10_chat_responses_uses_input),
        ("ChatResultPreview.tsx exists", check_11_chat_preview_exists),
        ("ChatResultPreview supports OpenAI choices", check_12_supports_openai_choices),
        ("ChatResultPreview supports Anthropic content", check_13_supports_anthropic_content),
        ("ChatResultPreview supports output_text", check_14_supports_responses_output_text),
        ("CapabilityRunner uses ChatResultPreview", check_15_runner_uses_chat_preview),
        ("chat.py enforces non-streaming", check_16_handlers_non_streaming),
        ("audit doc A-class has both", check_17_audit_doc_a_class),
        ("audit doc B-class retains chat-responses-tokens", check_18_audit_doc_b_class),
        ("ChatResultPreview has getTextBlockText helper", check_19_has_get_text_block_helper),
        ("ChatResultPreview supports output_text type block", check_20_supports_output_text_type_block),
        ("ChatResultPreview supports bare content block", check_21_supports_bare_content_block),
        ("ChatResultPreview supports nested data.content", check_22_supports_nested_data_content),
    ]

    all_passed = True
    for i, (name, fn) in enumerate(checks, 1):
        print(f"\n[{i}/{len(checks)}] {name}")
        try:
            result = fn()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"FAIL: {name} — {e}")
            all_passed = False

    print()
    if all_passed:
        print(f"All {len(checks)} chat runner closure checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
