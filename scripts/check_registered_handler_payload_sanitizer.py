#!/usr/bin/env python3
"""Check that registered /api/invoke handlers strip control fields before calling MiniMax.

Verifies the actual handler functions (image_t2i, image_i2i, music_gen) that are
invoked via /api/invoke/{cap_id} — not through CapabilityInvoker.

Covers:
  1. image_t2i strips confirm_asset_source and preserves business fields
  2. image_i2i strips confirm_asset_source and preserves business fields
  3. music_gen strips confirm_quota and preserves business fields
  4. Original payload is not modified (by reference check)
  5. All control fields are absent from provider payload
  6. lyrics_gen is unaffected (no confirm fields expected)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))

# Control fields that must NOT reach MiniMax
CONTROL_FIELDS = frozenset({
    "confirm_asset_source",
    "confirm_quota",
    "confirm_high_cost",
    "confirm_destructive",
    "confirm_long_running",
    "confirm_existing_task",
    "confirm_paid",
    "confirm_very_large_quota",
})


def find_and_load_handler(cap_id: str):
    """Load the registered handler function for a capability id."""
    # The registry is populated via @register_handler decorators.
    # Importing the modules triggers registration.
    from app.capabilities import image, music, voice, chat, files, models

    # Map cap_id → (module, function_name)
    HANDLERS = {
        "image-t2i": (image, "image_t2i"),
        "image-i2i": (image, "image_i2i"),
        "music-gen": (music, "music_gen"),
        "lyrics-gen": (music, "lyrics_gen"),
        "tts-sync": (voice, "tts_sync"),
    }
    if cap_id not in HANDLERS:
        raise ValueError(f"No known handler for {cap_id!r}")
    mod, fn_name = HANDLERS[cap_id]
    return getattr(mod, fn_name)


async def run_handler_capture(cap_id: str, payload: dict) -> dict:
    """Call the registered handler with payload, intercepting post_json.

    Returns the body dict that was passed to post_json (captured via mock).
    """
    captured_body: dict = {}

    async def mock_post_json(path: str, body: dict, *, with_group: bool = False, timeout: float = 120.0) -> Any:
        captured_body.update(body)
        # Return a dummy response so the handler doesn't crash
        if "image" in path:
            return {"base_resp": {"status_code": 0}, "data": {"image_urls": []}}
        if "music" in path:
            return {"base_resp": {"status_code": 0}, "data": {"audio_url": "https://example.com/test.mp3"}}
        return {}

    handler = find_and_load_handler(cap_id)

    with patch("app.capabilities.image.post_json", mock_post_json), \
         patch("app.capabilities.music.post_json", mock_post_json):
        result = await handler(payload)

    return captured_body


async def test_image_t2i():
    """image_t2i handler strips confirm_asset_source before calling post_json."""
    original = {
        "model": "image-01",
        "prompt": "一只橘猫",
        "aspect_ratio": "1:1",
        "confirm_asset_source": True,
        "confirm_quota": True,  # should also be stripped
    }
    original_copy = dict(original)

    captured = await run_handler_capture("image-t2i", original)

    # Original must not be mutated
    assert original == original_copy, f"Original payload was mutated! {original} != {original_copy}"

    # Control fields must not be in captured payload
    for field in CONTROL_FIELDS:
        assert field not in captured, f"Control field {field!r} should not reach MiniMax"

    # Business fields must be present
    assert captured.get("model") == "image-01", f"model missing: {captured}"
    assert captured.get("prompt") == "一只橘猫", f"prompt missing: {captured}"
    assert captured.get("aspect_ratio") == "1:1", f"aspect_ratio missing: {captured}"

    print("PASS: image_t2i strips all control fields, preserves business fields, does not mutate original")


async def test_image_i2i():
    """image_i2i handler strips confirm_asset_source before calling post_json."""
    original = {
        "model": "image-01",
        "prompt": "保持主体不变，改为电影感光影",
        "subject_reference": [{"type": "character", "image_file": "https://example.com/cat.jpg"}],
        "confirm_asset_source": True,
        "extra_field": "should be preserved",
    }
    original_copy = dict(original)

    captured = await run_handler_capture("image-i2i", original)

    assert original == original_copy, f"Original payload was mutated! {original} != {original_copy}"

    for field in CONTROL_FIELDS:
        assert field not in captured, f"Control field {field!r} should not reach MiniMax"

    assert captured.get("model") == "image-01"
    assert captured.get("prompt") == "保持主体不变，改为电影感光影"
    assert captured.get("subject_reference") == original["subject_reference"]
    assert captured.get("extra_field") == "should be preserved"

    print("PASS: image_i2i strips all control fields, preserves business fields, does not mutate original")


async def test_music_gen():
    """music_gen handler strips confirm_quota before calling post_json."""
    original = {
        "model": "music-2.6",
        "lyrics": "[verse]\n夏日晚风\n\n[chorus]\n",
        "prompt": "温柔、怀旧、民谣",
        "title": "夏日晚风",
        "confirm_quota": True,
        "confirm_asset_source": True,
    }
    original_copy = dict(original)

    captured = await run_handler_capture("music-gen", original)

    assert original == original_copy, f"Original payload was mutated! {original} != {original_copy}"

    for field in CONTROL_FIELDS:
        assert field not in captured, f"Control field {field!r} should not reach MiniMax"

    assert captured.get("model") == "music-2.6"
    assert captured.get("lyrics") == "[verse]\n夏日晚风\n\n[chorus]\n"
    assert captured.get("prompt") == "温柔、怀旧、民谣"
    assert captured.get("title") == "夏日晚风"

    print("PASS: music_gen strips all control fields, preserves business fields, does not mutate original")


async def test_lyrics_gen_unchanged():
    """lyrics_gen has no confirm fields — should pass through unchanged."""
    original = {
        "mode": "write_full_song",
        "prompt": "夏天傍晚的乡村小路",
        "title": "夏日晚风",
    }
    original_copy = dict(original)

    captured = await run_handler_capture("lyrics-gen", original)

    assert captured == original, f"lyrics_gen should pass payload unchanged, got: {captured}"
    print("PASS: lyrics_gen passes payload unchanged")


async def main():
    print("=" * 60)
    print("Registered Handler Payload Sanitizer checks")
    print("=" * 60)

    tests = [
        test_image_t2i,
        test_image_i2i,
        test_music_gen,
        test_lyrics_gen_unchanged,
    ]

    all_passed = True
    for t in tests:
        try:
            await t()
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            all_passed = False

    print()
    if all_passed:
        print("All registered handler sanitizer checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
