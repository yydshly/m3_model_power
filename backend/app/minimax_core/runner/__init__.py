"""Runner template loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_runner_dir = Path(__file__).resolve().parent
_TEMPLATES_FILE = _runner_dir / "capability_runner_templates.json"

_SUPPORTED_CAPABILITIES = {"lyrics-gen", "tts-sync", "voice-list", "image-t2i", "chat-openai", "music-gen", "image-i2i"}


def load_runner_templates() -> dict[str, Any]:
    with _TEMPLATES_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("templates", {})


def get_runner_template(capability_id: str) -> dict[str, Any] | None:
    templates = load_runner_templates()
    return templates.get(capability_id)


def is_runner_supported(capability_id: str) -> bool:
    return capability_id in _SUPPORTED_CAPABILITIES
