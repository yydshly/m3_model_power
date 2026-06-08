"""Runner template loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..registry.loader import get_capability_registry

_runner_dir = Path(__file__).resolve().parent
_TEMPLATES_FILE = _runner_dir / "capability_runner_templates.json"

_SUPPORTED_CAPABILITIES = {"lyrics-gen", "tts-sync", "voice-list", "tts-async", "image-t2i", "chat-openai", "chat-anthropic", "chat-responses-create", "music-gen", "image-i2i", "file-upload", "file-list", "file-retrieve", "file-content"}


def load_runner_templates() -> dict[str, Any]:
    with _TEMPLATES_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    templates = data.get("templates", {})

    # Enrich each template with billing_policy and cost_level from the capability registry
    registry = get_capability_registry()
    for cap_id, template in templates.items():
        cap = registry.by_id(cap_id)
        if cap:
            template["billing_policy"] = {
                "billing_category": cap.billing_policy.billing_category,
                "requires_explicit_confirmation": cap.billing_policy.requires_explicit_confirmation,
                "may_charge_extra": cap.billing_policy.may_charge_extra,
                "consumes_token_plan_quota": cap.billing_policy.consumes_token_plan_quota,
                "requires_certification": cap.billing_policy.requires_certification,
                "requires_uploaded_asset": cap.billing_policy.requires_uploaded_asset,
                "billing_note": cap.billing_policy.billing_note,
                "official_pricing_note": cap.billing_policy.official_pricing_note,
            }
            template["cost_level"] = cap.cost_level
        else:
            # Fallback defaults
            template["billing_policy"] = {
                "billing_category": "normal_token_plan_test",
                "requires_explicit_confirmation": False,
                "may_charge_extra": False,
                "consumes_token_plan_quota": True,
                "requires_certification": False,
                "requires_uploaded_asset": False,
                "billing_note": "",
                "official_pricing_note": "",
            }
            template["cost_level"] = "low"

    return templates


def get_runner_template(capability_id: str) -> dict[str, Any] | None:
    templates = load_runner_templates()
    return templates.get(capability_id)


def is_runner_supported(capability_id: str) -> bool:
    return capability_id in _SUPPORTED_CAPABILITIES
