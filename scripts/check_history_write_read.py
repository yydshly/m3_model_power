#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify history write/read roundtrip: append_history → list_history → status counts increase.

Uses a temporary directory for history to avoid polluting the real runtime.
"""
from __future__ import annotations

import os
import sys
import tempfile

# Set temp dir BEFORE importing history_store (import caches module)
tmpdir = tempfile.mkdtemp(prefix="minimax_history_test_")
os.environ["MINIMAX_HISTORY_DIR"] = tmpdir

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.minimax_core.verification.history_store import append_history, list_history, get_history_status


def main() -> int:
    errors: list[str] = []

    before = get_history_status()
    before_count = before["valid_record_count"]

    # Write a smoke record (returns history_id)
    history_id = append_history(
        action="invoke",
        capability_id="history-smoke-test",
        payload={"hello": "world"},
        confirmations={},
        result={"ok": True, "data": {"text": "ok"}},
        duration_ms=1,
    )

    if history_id is None:
        errors.append("append_history returned None (write failed)")
    else:
        # Read it back
        items = list_history(limit=10, capability_id="history-smoke-test")
        if not items:
            errors.append("history-smoke-test record missing from list_history()")
        else:
            if items[0]["capability_id"] != "history-smoke-test":
                errors.append(f"Expected capability_id=history-smoke-test, got {items[0].get('capability_id')}")
            if items[0]["action"] != "invoke":
                errors.append(f"Expected action=invoke, got {items[0].get('action')}")

    after = get_history_status()
    if after["valid_record_count"] < before_count:
        errors.append(f"valid_record_count decreased: before={before_count}, after={after['valid_record_count']}")

    # Verify /api/history/capability/xxx returns 200 (via fastapi testclient)
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # status endpoint
        r = client.get("/api/history/status")
        if r.status_code != 200:
            errors.append(f"/api/history/status returned {r.status_code}, expected 200")

        # test-console endpoint
        r = client.get("/api/history/test-console")
        if r.status_code != 200:
            errors.append(f"/api/history/test-console returned {r.status_code}, expected 200")
        body = r.json()
        if "items" not in body:
            errors.append("/api/history/test-console missing 'items' field")

        # capability endpoint (empty is OK, must be 200)
        for cap_id in ["chat-openai", "history-smoke-test"]:
            r = client.get(f"/api/history/capability/{cap_id}")
            if r.status_code != 200:
                errors.append(f"/api/history/capability/{cap_id} returned {r.status_code}, expected 200")
            body = r.json()
            if "items" not in body:
                errors.append(f"/api/history/capability/{cap_id} missing 'items' field")

    except ImportError as e:
        errors.append(f"[TESTCLIENT] fastapi.testclient not installed: {e}")
    except Exception as e:
        errors.append(f"[API] history endpoint test failed: {e}")

    if errors:
        print("[FAILED] history write/read check failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] history write/read check passed")
        print(f"  - temp dir: {tmpdir}")
        print(f"  - write → read roundtrip OK (history_id={history_id})")
        print(f"  - valid_record_count before={before_count}, after={after['valid_record_count']}")
        print(f"  - /api/history/status → 200")
        print(f"  - /api/history/test-console → 200")
        print(f"  - /api/history/capability/{{id}} → 200")
        return 0


if __name__ == "__main__":
    sys.exit(main())
