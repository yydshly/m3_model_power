#!/usr/bin/env python3
"""Check startup script contract: start.py, scripts/dev.py, docs/RUNBOOK.md exist and are correct."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors: list[str] = []

    start_py = _ROOT / "start.py"
    dev_py = _ROOT / "scripts" / "dev.py"
    runbook = _ROOT / "docs" / "RUNBOOK.md"

    # 1. start.py exists
    if not start_py.exists():
        print(f"FAIL: start.py does not exist at {start_py}")
        errors.append("start.py not found")
    else:
        print("PASS: start.py exists")

    # 2. scripts/dev.py exists
    if not dev_py.exists():
        print(f"FAIL: scripts/dev.py does not exist at {dev_py}")
        errors.append("scripts/dev.py not found")
    else:
        print("PASS: scripts/dev.py exists")

    # 3. docs/RUNBOOK.md exists
    if not runbook.exists():
        print(f"FAIL: docs/RUNBOOK.md does not exist at {runbook}")
        errors.append("docs/RUNBOOK.md not found")
    else:
        print("PASS: docs/RUNBOOK.md exists")

    # 4. start.py default param is dev
    if start_py.exists():
        content = start_py.read_text(encoding="utf-8")
        if '["dev"]' in content or '["dev"]' in content or "[\"dev\"]" in content:
            print("PASS: start.py defaults to dev")
        else:
            print("FAIL: start.py does not default to dev")
            errors.append("start.py missing default dev param")

    # 5. scripts/dev.py contains all required commands
    if dev_py.exists():
        content = dev_py.read_text(encoding="utf-8")
        for cmd in ["doctor", "install", "dev", "backend", "frontend", "check", "build", "clean", "stop"]:
            if f'"{cmd}"' in content or f"'{cmd}'" in content:
                print(f"PASS: scripts/dev.py contains '{cmd}'")
            else:
                print(f"FAIL: scripts/dev.py missing '{cmd}'")
                errors.append(f"scripts/dev.py missing command: {cmd}")

    # 6. RUNBOOK.md contains required content
    if runbook.exists():
        content = runbook.read_text(encoding="utf-8")
        checks = {
            "python start.py": "python start.py",
            "python start.py install": "python start.py install",
            "python start.py doctor": "python start.py doctor",
            "8777": "8777",
            "5175": "5175",
            "/api/history/probe": "/api/history/probe",
            "runtime": "runtime",
        }
        for phrase, label in checks.items():
            if phrase in content:
                print(f"PASS: RUNBOOK.md contains '{label}'")
            else:
                print(f"FAIL: RUNBOOK.md missing '{label}'")
                errors.append(f"RUNBOOK.md missing: {label}")

    if errors:
        print(f"\n[FAILED] {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\n[PASSED] Startup contract check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
