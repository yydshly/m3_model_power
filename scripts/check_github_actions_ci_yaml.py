#!/usr/bin/env python3
"""检查 GitHub Actions CI YAML 文件的语法完整性。"""
import sys
import yaml
from pathlib import Path


def main():
    errors = []

    path = Path(".github/workflows/ci.yml")
    if not path.exists():
        errors.append(".github/workflows/ci.yml not found")
        print("[FAILED]")
        for err in errors:
            print(f"  - {err}")
        return 1

    content = path.read_text(encoding="utf-8")

    # 检查常见 YAML 语法错误
    if "run |" in content:
        errors.append("Invalid GitHub Actions syntax: 'run |' should be 'run: |'")

    try:
        data = yaml.safe_load(content)
        if data is None:
            errors.append("YAML parsed as null — empty or invalid file")
        elif not isinstance(data, dict):
            errors.append(f"YAML root must be a mapping, got {type(data).__name__}")
    except yaml.YAMLError as exc:
        errors.append(f"YAML parse failed: {exc}")

    # 检查必需项
    required_terms = [
        "pull_request",
        "push",
        "Run guard scripts",
        "Compile Python",
        "Typecheck and build",
    ]
    for term in required_terms:
        if term not in content:
            errors.append(f"Missing required term: '{term}'")

    if errors:
        print(f"[FAILED] {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[PASSED] GitHub Actions CI YAML is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
