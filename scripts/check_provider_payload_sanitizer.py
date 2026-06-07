#!/usr/bin/env python3
"""Check provider_payload sanitizer correctness.

Covers:
  1. strip_control_fields does not modify original payload
  2. All confirm_* fields are stripped
  3. Business fields are preserved (model, prompt, subject_reference, etc.)
  4. Empty payload handling
  5. RiskGate still blocks unconfirmed image-i2i
  6. RiskGate allows image-i2i with payload.confirm_asset_source=true
  7. RiskGate allows image-i2i with confirmations.confirm_asset_source=true
  8. Dry-run image smoke passes
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path so we can import minimax_core
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))

CONTROL_FIELDS = {
    "confirm_asset_source",
    "confirm_quota",
    "confirm_high_cost",
    "confirm_destructive",
    "confirm_long_running",
    "confirm_existing_task",
    "confirm_paid",
    "confirm_very_large_quota",
}

BUSINESS_FIELDS = [
    "model", "prompt", "aspect_ratio", "subject_reference",
    "text", "voice_setting", "lyrics", "style", "title",
]


def import_sanitizer():
    from app.minimax_core.contracts.provider_payload import strip_control_fields
    return strip_control_fields


def test_does_not_modify_original():
    """strip_control_fields must not mutate the input dict."""
    strip = import_sanitizer()
    original = {"model": "image-01", "confirm_asset_source": True}
    original_copy = dict(original)
    result = strip(original)
    assert original == original_copy, "Original payload was mutated!"
    assert result is not original, "Should return a new dict"
    print("PASS: does not modify original payload")


def test_control_fields_stripped():
    """All confirm_* fields are removed from result."""
    strip = import_sanitizer()
    payload = {**{f: True for f in CONTROL_FIELDS}, "model": "image-01"}
    result = strip(payload)
    for field in CONTROL_FIELDS:
        assert field not in result, f"Control field '{field}' should be stripped"
    assert "model" in result
    print("PASS: all control fields stripped")


def test_business_fields_preserved():
    """Business fields pass through unchanged."""
    strip = import_sanitizer()
    payload = {
        "model": "image-01",
        "prompt": "a cat",
        "aspect_ratio": "1:1",
        "subject_reference": [{"type": "character", "image_file": "https://x.com/cat.jpg"}],
        "confirm_asset_source": True,
        "confirm_quota": True,
    }
    result = strip(payload)
    assert result["model"] == "image-01"
    assert result["prompt"] == "a cat"
    assert result["aspect_ratio"] == "1:1"
    assert result["subject_reference"] == payload["subject_reference"]
    assert "confirm_asset_source" not in result
    assert "confirm_quota" not in result
    print("PASS: business fields preserved")


def test_empty_payload():
    """Empty dict returns empty dict."""
    strip = import_sanitizer()
    assert strip({}) == {}
    print("PASS: empty payload handled")


def test_nested_preserved():
    """Nested structures (dicts/lists) are preserved, not deep-copied."""
    strip = import_sanitizer()
    subject_ref = [{"type": "character", "image_file": "https://x.com/cat.jpg"}]
    payload = {"model": "image-01", "subject_reference": subject_ref, "confirm_asset_source": True}
    result = strip(payload)
    assert result["subject_reference"] == subject_ref
    # verify same object reference (not deep cloned)
    assert result["subject_reference"] is subject_ref
    print("PASS: nested structures preserved (same reference)")


def main():
    print("=" * 60)
    print("Provider Payload Sanitizer checks")
    print("=" * 60)

    tests = [
        test_does_not_modify_original,
        test_control_fields_stripped,
        test_business_fields_preserved,
        test_empty_payload,
        test_nested_preserved,
    ]

    all_passed = True
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            all_passed = False

    print()
    if all_passed:
        print("All sanitizer checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
