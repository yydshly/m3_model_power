#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify invoke router history integration: base_resp normalization, history_id in responses.

Uses monkeypatched handlers to avoid real MiniMax upstream calls in CI.
"""
from __future__ import annotations

import os
import sys
import tempfile

# Set temp dir BEFORE importing history_store
tmpdir = tempfile.mkdtemp(prefix="minimax_invoke_test_")
os.environ["MINIMAX_HISTORY_DIR"] = tmpdir

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def main() -> int:
    errors: list[str] = []

    # ── 1. Test _extract_base_resp_error ─────────────────────────────────────────
    try:
        from app.routers.invoke import _extract_base_resp_error

        # status_code == 0 → None
        r0 = _extract_base_resp_error({"base_resp": {"status_code": 0}})
        if r0 is not None:
            errors.append(f"_extract_base_resp_error({{status_code:0}}) must return None, got {r0}")

        # status_code == 2013 → minimax_business_error
        r2013 = _extract_base_resp_error({"base_resp": {"status_code": 2013, "status_msg": "invalid params, empty field"}})
        if r2013 is None:
            errors.append("_extract_base_resp_error({status_code:2013}) returned None, expected minimax_business_error")
        elif r2013.get("error") != "minimax_business_error":
            errors.append(f"error field: expected 'minimax_business_error', got {r2013.get('error')}")
        elif r2013.get("status") != 2013:
            errors.append(f"status field: expected 2013, got {r2013.get('status')}")
        elif "invalid params" not in str(r2013.get("message", "")):
            errors.append(f"message field: expected 'invalid params', got {r2013.get('message')}")

        # non-dict result → None
        rstr = _extract_base_resp_error("not a dict")
        if rstr is not None:
            errors.append("_extract_base_resp_error('not a dict') must return None")

        # no base_resp → None
        rno = _extract_base_resp_error({"data": 123})
        if rno is not None:
            errors.append("_extract_base_resp_error({data:123}) must return None")

    except ImportError as e:
        errors.append(f"[INVOKE] Cannot import _extract_base_resp_error: {e}")

    # ── 2. Test append_history returns history_id ─────────────────────────────────
    try:
        from app.minimax_core.verification.history_store import append_history, list_history

        history_id = append_history(
            action="invoke",
            capability_id="invoke-integration-test",
            payload={"model": "MiniMax-M3", "input": "hello"},
            confirmations={},
            result={"ok": True, "data": {"text": "hello"}},
            duration_ms=5,
        )
        if history_id is None:
            errors.append("append_history returned None (write failed)")
        else:
            items = list_history(limit=10, capability_id="invoke-integration-test")
            if not items:
                errors.append("invoke-integration-test record missing after append_history")
            elif items[0]["id"] != history_id:
                errors.append(f"list_history returned id {items[0]['id']}, expected {history_id}")

    except ImportError as e:
        errors.append(f"[STORE] Cannot import history_store: {e}")

    # ── 3. Test FastAPI invoke endpoint with monkeypatched handlers ───────────────
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        from app.registry import handlers as handlers_module

        client = TestClient(app)

        # Save original handlers
        original_chat_handler = handlers_module.HANDLERS.get("chat-openai")
        original_tts_handler = handlers_module.HANDLERS.get("tts-sync")

        # Monkeypatched handlers
        async def fake_chat_success(payload):
            return {
                "choices": [
                    {"message": {"role": "assistant", "content": "hello from fake handler"}}
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 4,
                    "total_tokens": 7,
                },
            }

        async def fake_tts_business_error(payload):
            return {
                "base_resp": {
                    "status_code": 2013,
                    "status_msg": "invalid params, empty field",
                }
            }

        try:
            # Apply monkeypatches
            handlers_module.HANDLERS["chat-openai"] = fake_chat_success
            handlers_module.HANDLERS["tts-sync"] = fake_tts_business_error

            # Test: chat-openai success → history_id returned
            r = client.post(
                "/api/invoke/chat-openai",
                json={
                    "payload": {
                        "model": "MiniMax-M2.7-highspeed",
                        "messages": [{"role": "user", "content": "hi"}],
                    }
                },
                headers={"X-MMW-Trace-ID": "test_invoke_success"},
            )
            body = r.json()
            if r.status_code != 200:
                errors.append(f"/api/invoke/chat-openai returned {r.status_code}: {body}")
            if "history_id" not in body:
                errors.append("/api/invoke/chat-openai response missing history_id field")
            if body.get("ok") is not True:
                errors.append(f"/api/invoke/chat-openai expected ok=true, got {body}")

            # Test: tts-sync base_resp business error → 400 + minimax_business_error
            r2 = client.post(
                "/api/invoke/tts-sync",
                json={
                    "payload": {
                        "model": "speech-02-turbo",
                        "text": "hello",
                        "voice_setting": {"voice_id": "fake_voice_id", "speed": 1},
                    }
                },
                headers={"X-MMW-Trace-ID": "test_invoke_business_error"},
            )
            body2 = r2.json()
            if r2.status_code != 400:
                errors.append(f"/api/invoke/tts-sync business error returned {r2.status_code}, expected 400: {body2}")
            if "history_id" not in body2:
                errors.append("/api/invoke/tts-sync response missing history_id field")
            if body2.get("error") != "minimax_business_error":
                errors.append(f"tts-sync error should be minimax_business_error, got {body2.get('error')}")
            if body2.get("status") != 2013:
                errors.append(f"tts-sync status should be 2013, got {body2.get('status')}")

        finally:
            # Restore original handlers
            if original_chat_handler is not None:
                handlers_module.HANDLERS["chat-openai"] = original_chat_handler
            else:
                handlers_module.HANDLERS.pop("chat-openai", None)

            if original_tts_handler is not None:
                handlers_module.HANDLERS["tts-sync"] = original_tts_handler
            else:
                handlers_module.HANDLERS.pop("tts-sync", None)

    except ImportError as e:
        errors.append(f"[TESTCLIENT] Cannot import: {e}")
    except Exception as e:
        errors.append(f"[API] invoke endpoint test failed: {e}")

    if errors:
        print("[FAILED] invoke history integration check failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] invoke history integration check passed")
        print(f"  - temp dir: {tmpdir}")
        print(f"  - _extract_base_resp_error normalizes non-zero status_code")
        print(f"  - append_history returns history_id")
        print(f"  - /api/invoke/chat-openai mock returns history_id")
        print(f"  - /api/invoke/tts-sync mock normalizes base_resp business error")
        return 0


if __name__ == "__main__":
    sys.exit(main())
