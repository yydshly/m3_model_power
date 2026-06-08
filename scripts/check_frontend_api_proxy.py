#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify frontend API proxy configuration: vite.config.ts defaults and .env.example."""
from __future__ import annotations

import os
import re
import sys


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ── 1. Check vite.config.ts default apiBase ────────────────────────────
    vite_cfg = os.path.join(base, "frontend", "vite.config.ts")
    if not os.path.exists(vite_cfg):
        errors.append(f"[VITE] {vite_cfg} not found")
    else:
        with open(vite_cfg, encoding="utf-8") as f:
            vite_src = f.read()

        # Must not default to localhost:8000
        if re.search(r"['\"]http://localhost:8000['\"]", vite_src):
            errors.append("[VITE] vite.config.ts still defaults to http://localhost:8000")

        # Must default to 127.0.0.1:8777
        if not re.search(r"['\"]http://127\.0\.0\.1:8777['\"]", vite_src):
            errors.append("[VITE] vite.config.ts does not default to http://127.0.0.1:8777")

        # Must preserve VITE_API_BASE_URL override
        if "VITE_API_BASE_URL" not in vite_src:
            errors.append("[VITE] vite.config.ts does not reference VITE_API_BASE_URL env var")

    # ── 2. Check .env.example exists and has correct default ───────────────
    env_example = os.path.join(base, "frontend", ".env.example")
    if not os.path.exists(env_example):
        errors.append("[ENV] frontend/.env.example not found")
    else:
        with open(env_example, encoding="utf-8") as f:
            env_src = f.read()

        if "VITE_API_BASE_URL" not in env_src:
            errors.append("[ENV] .env.example does not contain VITE_API_BASE_URL")
        elif "http://127.0.0.1:8777" not in env_src:
            errors.append("[ENV] .env.example VITE_API_BASE_URL is not set to http://127.0.0.1:8777")

    # ── 3. Ensure .env is not committed ───────────────────────────────────
    dotenv = os.path.join(base, "frontend", ".env")
    if os.path.exists(dotenv):
        warnings.append("[ENV] frontend/.env exists — ensure it is in .gitignore")

    if errors:
        print("[FAILED] frontend API proxy check failed:")
        for e in errors:
            print(f"  - {e}")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 1
    else:
        print("[PASSED] frontend API proxy check passed")
        if warnings:
            print(f"\n[WARNINGS] {len(warnings)}:")
            for w in warnings:
                print(f"  - {w}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
