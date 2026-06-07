#!/usr/bin/env python3
"""验证 history_store.py 的核心函数行为。"""
import sys
from pathlib import Path

# 确保 backend 模块路径可导入
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from backend.app.minimax_core.verification.history_store import (
    normalize_limit,
    redact_value,
    summarize_payload,
    _is_sensitive_key,
)


def test_normalize_limit():
    assert normalize_limit(None) == 50, f"normalize_limit(None) got {normalize_limit(None)}"
    assert normalize_limit(-1) == 1, f"normalize_limit(-1) got {normalize_limit(-1)}"
    assert normalize_limit(0) == 1, f"normalize_limit(0) got {normalize_limit(0)}"
    assert normalize_limit(9999) == 200, f"normalize_limit(9999) got {normalize_limit(9999)}"
    assert normalize_limit(100) == 100, f"normalize_limit(100) got {normalize_limit(100)}"
    assert normalize_limit("abc") == 50, f"normalize_limit('abc') got {normalize_limit('abc')}"
    print("normalize_limit: PASS")


def test_is_sensitive_key():
    # Exact matches
    assert _is_sensitive_key("api_key") is True
    assert _is_sensitive_key("authorization") is True
    assert _is_sensitive_key("access_token") is True
    assert _is_sensitive_key("refresh_token") is True
    assert _is_sensitive_key("id_token") is True
    assert _is_sensitive_key("client_secret") is True
    assert _is_sensitive_key("jwt") is True
    assert _is_sensitive_key("cookie") is True
    assert _is_sensitive_key("session_id") is True
    # Substrings
    assert _is_sensitive_key("my_secret_key") is True
    assert _is_sensitive_key("auth_token") is True
    assert _is_sensitive_key("user_password") is True
    assert _is_sensitive_key("x_custom_header") is True
    # Non-sensitive
    assert _is_sensitive_key("text") is False
    assert _is_sensitive_key("model") is False
    assert _is_sensitive_key("task_id") is False
    assert _is_sensitive_key("file_id") is False
    print("_is_sensitive_key: PASS")


def test_redact_value_flat():
    assert redact_value("hello") == "hello"
    assert redact_value(42) == 42
    assert redact_value(True) is True
    assert redact_value(None) is None
    print("redact_value (flat): PASS")


def test_redact_value_nested():
    payload = {
        "text": "hello world",
        "api_key": "sk-12345678",
        "model": "minimax-text-01",
        "headers": {
            "authorization": "Bearer sk-xxx",
            "content_type": "application/json",
        },
        "nested": {
            "deep": {
                "access_token": "tok XYZ",
            }
        },
    }
    redacted = redact_value(payload)
    assert redacted["text"] == "hello world"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["model"] == "minimax-text-01"
    assert redacted["headers"]["authorization"] == "[REDACTED]"
    assert redacted["headers"]["content_type"] == "application/json"
    assert redacted["nested"]["deep"]["access_token"] == "[REDACTED]"
    print("redact_value (nested): PASS")


def test_redact_value_list():
    payload = {
        "items": ["a" * 500, "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"],
        "data": ["tok1", "tok2"],  # "data" is not sensitive
    }
    redacted = redact_value(payload)
    assert len(redacted["items"]) == 10  # capped at 10
    assert redacted["items"][0] == "a" * 200  # str capped at 200
    assert redacted["data"] == ["tok1", "tok2"]  # non-sensitive list preserved
    print("redact_value (list): PASS")


def test_redact_value_depth_limit():
    # At depth 3, dict is still processed; at depth 4 (depth > 3), returns "[TRUNCATED_DEPTH]"
    deep = {"l1": {"l2": {"l3": {"l4": "secret"}}}}
    redacted = redact_value(deep)
    # depth 3: l3 dict -> {"l4": "[TRUNCATED_DEPTH]"} (depth 4 exceeds limit)
    assert redacted["l1"]["l2"]["l3"]["l4"] == "[TRUNCATED_DEPTH]"
    print("redact_value (depth limit): PASS")


def test_summarize_payload_no_sensitive_keys():
    payload = {
        "text": "hello",
        "model": "minimax-text-01",
    }
    summary = summarize_payload(payload)
    assert "text" in summary["payload_keys"]
    assert "model" in summary["payload_keys"]
    assert "api_key" not in summary["payload_keys"]
    assert "[REDACTED]" not in summary["payload_preview"]
    assert summary["payload_size_chars"] > 0
    print("summarize_payload (no sensitive): PASS")


def test_summarize_payload_with_sensitive():
    payload = {
        "text": "hello",
        "api_key": "sk-real",
        "nested": {
            "authorization": "Bearer tok",
        },
    }
    summary = summarize_payload(payload)
    assert "api_key" not in summary["payload_keys"]
    assert "authorization" not in summary["payload_keys"]
    assert "[REDACTED]" in summary["payload_preview"]
    assert "sk-real" not in summary["payload_preview"]
    assert "Bearer tok" not in summary["payload_preview"]
    print("summarize_payload (with sensitive): PASS")


def test_preview_length():
    payload = {"text": "a" * 1000}
    summary = summarize_payload(payload)
    assert len(summary["payload_preview"]) <= 503  # 500 + "..."
    print(f"preview length {len(summary['payload_preview'])}: PASS")


if __name__ == "__main__":
    test_normalize_limit()
    test_is_sensitive_key()
    test_redact_value_flat()
    test_redact_value_nested()
    test_redact_value_list()
    test_redact_value_depth_limit()
    test_summarize_payload_no_sensitive_keys()
    test_summarize_payload_with_sensitive()
    test_preview_length()
    print("\nAll tests PASSED")
