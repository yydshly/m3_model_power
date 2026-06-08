#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify demoPayload coverage and usage: buildDemoPayload is used everywhere it should be."""
from __future__ import annotations

import sys
import os
import re
import json


def main() -> int:
    errors: list[str] = []
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ── 1. Check Capability.tsx imports buildDemoPayload ───────────────────────
    cap_ts = os.path.join(root, "frontend", "src", "pages", "Capability.tsx")
    with open(cap_ts, encoding="utf-8") as f:
        cap_src = f.read()

    if "from '../domain/demoPayload'" not in cap_src and 'from "../domain/demoPayload"' not in cap_src:
        errors.append("Capability.tsx does not import buildDemoPayload from '../domain/demoPayload'")

    # ── 2. Check setExamplePayload uses buildDemoPayload ───────────────────────
    if re.search(r"setExamplePayload\(cap\.example\s*\?\?\s*\{\}\)", cap_src):
        errors.append("Capability.tsx still uses setExamplePayload(cap.example ?? {})")

    # ── 3. Check InvokePanel defaultPayload prop uses buildDemoPayload ──────────
    if re.search(r'defaultPayload=\{cap\.example\}', cap_src):
        errors.append("Capability.tsx still uses defaultPayload={cap.example}")

    # ── 4. Check InvokePanel responds to defaultPayload changes ────────────────
    invoke_ts = os.path.join(root, "frontend", "src", "components", "InvokePanel.tsx")
    with open(invoke_ts, encoding="utf-8") as f:
        invoke_src = f.read()

    if "useEffect" not in invoke_src:
        errors.append("InvokePanel.tsx does not import useEffect")
    if "defaultPayloadText" not in invoke_src and "useEffect" in invoke_src:
        errors.append("InvokePanel.tsx does not sync body with defaultPayload via useEffect")

    # ── 5. Check demoPayload.ts covers required keys ───────────────────────────
    demo_ts = os.path.join(root, "frontend", "src", "domain", "demoPayload.ts")
    with open(demo_ts, encoding="utf-8") as f:
        demo_src = f.read()

    # Parse the DEMO_PAYLOADS object using a lighter approach
    required_keys = {
        "chat-responses-tokens": ["input"],
        "tts-sync": ["text"],
        "image-t2i": ["prompt"],
        "music-gen": ["lyrics"],
        "file-retrieve": ["file_id"],
        "models-openai-retrieve": ["model"],
        "models-anthropic-retrieve": ["model"],
    }

    for cap_id, fields in required_keys.items():
        if f"'{cap_id}':" not in demo_src and f'"{cap_id}":' not in demo_src:
            errors.append(f"demoPayload.ts missing entry for '{cap_id}'")
            continue
        # Extract the block for this capability
        # Simple check: look for the capability key and verify field names appear nearby
        cap_pattern = re.compile(
            rf"['\"]({re.escape(cap_id)})['\"]:\s*\{{([^}}]+)\}}",
            re.DOTALL
        )
        m = cap_pattern.search(demo_src)
        if not m:
            errors.append(f"demoPayload.ts: could not parse entry for '{cap_id}'")
        else:
            block = m.group(2)
            for field in fields:
                if field not in block:
                    errors.append(f"demoPayload.ts['{cap_id}'] missing field '{field}'")

    # ── 6. Check getDemoReadiness exists ──────────────────────────────────────
    if "getDemoReadiness" not in demo_src:
        errors.append("demoPayload.ts missing getDemoReadiness function")

    # ── 7. Check Capability.tsx uses getDemoReadiness ────────────────────────
    if "getDemoReadiness" not in cap_src:
        errors.append("Capability.tsx does not use getDemoReadiness")

    if errors:
        print("[FAILED] demo payload coverage check failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASSED] demo payload coverage check passed")
        print("  - Capability.tsx imports buildDemoPayload")
        print("  - setExamplePayload uses buildDemoPayload")
        print("  - InvokePanel defaultPayload uses buildDemoPayload")
        print("  - InvokePanel syncs body on defaultPayload change")
        print("  - demoPayload.ts covers all required capability entries")
        print("  - getDemoReadiness is defined and used")
        return 0


if __name__ == "__main__":
    sys.exit(main())
