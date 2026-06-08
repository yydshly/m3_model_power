#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime smoke guard: verify FastAPI app imports and core read-only API endpoints.

Checks:
1. app.main imports without ImportError
2. app.routers.runner imports
3. load_runner_templates() returns non-empty dict
4. FastAPI TestClient can access core read-only endpoints
"""
from __future__ import annotations

import sys


def main() -> int:
    errors: list[str] = []

    # ── 1. Import app.main ──────────────────────────────────────────────────────
    try:
        from app.main import app  # noqa: F401
    except ImportError as e:
        errors.append(f"[IMPORT] Failed to import app.main: {e}")
        # Can't continue if main itself doesn't import
        print("[FAILED] Cannot import app.main — fix required before any other checks")
        for e in errors:
            print(f"  - {e}")
        return 1

    # ── 2. Import runner router ────────────────────────────────────────────────
    try:
        from app.routers import runner  # noqa: F401
    except ImportError as e:
        errors.append(f"[IMPORT] Failed to import app.routers.runner: {e}")

    # ── 3. Import and run load_runner_templates ─────────────────────────────────
    try:
        from app.minimax_core.runner import load_runner_templates
        templates = load_runner_templates()
        if not isinstance(templates, dict):
            errors.append("[RUNNER] load_runner_templates() must return a dict")
        if not templates:
            errors.append("[RUNNER] load_runner_templates() returned empty dict")
        required = ["voice-list", "chat-openai", "chat-anthropic"]
        for cap_id in required:
            if cap_id not in templates:
                errors.append(f"[RUNNER] Required template '{cap_id}' missing from load_runner_templates()")
    except ImportError as e:
        errors.append(f"[IMPORT] Failed to import load_runner_templates: {e}")
    except Exception as e:
        errors.append(f"[RUNNER] load_runner_templates() raised: {e}")

    # ── 4. Smoke-test read-only API endpoints via TestClient ─────────────────────
    try:
        from fastapi.testclient import TestClient

        client = TestClient(app)

        endpoints = [
            ("/api/health", 200),
            ("/api/registry", 200),
            ("/api/runner/templates", 200),
            ("/api/workflows", 200),
            ("/api/scenarios", 200),
            ("/api/history/status", 200),
        ]

        for path, expected_status in endpoints:
            try:
                resp = client.get(path)
                if resp.status_code != expected_status:
                    errors.append(
                        f"[API] {path} returned {resp.status_code}, expected {expected_status}"
                    )
            except Exception as e:
                errors.append(f"[API] {path} raised: {e}")
    except ImportError:
        errors.append("[TESTCLIENT] fastapi.testclient not installed — pip install fastapi first")
    except Exception as e:
        errors.append(f"[TESTCLIENT] TestClient smoke failed: {e}")

    if errors:
        print(f"[FAILED] {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] Runtime smoke check passed")
        print("  - app.main imports OK")
        print("  - app.routers.runner imports OK")
        print("  - load_runner_templates() returns non-empty dict")
        print("  - All read-only API endpoints returned 200")
        return 0


if __name__ == "__main__":
    sys.exit(main())
