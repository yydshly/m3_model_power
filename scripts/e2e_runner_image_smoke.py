#!/usr/bin/env python3
"""
Image smoke test for Guided Capability Runner.

Validates the image-t2i → image-i2i product loop:
  1. Check health
  2. Load runner templates
  3. Verify image-t2i and image-i2i templates exist
  4. (With --execute-real) Call image-t2i to generate an image
  5. Extract image URL from response
  6. (With --execute-real) image-i2i risk-check unconfirmed (should block)
  7. (With --execute-real) image-i2i risk-check confirmed (should allow)
  8. (With --execute-real --confirm-asset-source) image-i2i invoke
  9. Verify image result in response

Safe by default: run without --execute-real for dry-run validation.
Real image-i2i invoke requires BOTH --execute-real AND --confirm-asset-source.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SEC = 30
IMAGE_INVOKE_TIMEOUT_SEC = 120

_KEY_TAIL_LEN = 6


def _mask_key(key: str | None) -> str:
    if not key:
        return "<not-set>"
    if len(key) <= _KEY_TAIL_LEN:
        return "****"
    return f"...{key[-_KEY_TAIL_LEN:]}"


def http_post(path: str, body: dict, token: str | None = None, timeout: int | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout or TIMEOUT_SEC) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {url}: {body_text}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error on {url}: {e}") from e


def http_get(path: str, token: str | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {url}: {body_text}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error on {url}: {e}") from e


def get_token() -> tuple[str | None, bool]:
    """Load MINIMAX_TOKEN_PLAN_KEY from backend/.env if present."""
    env_path = _ROOT / "backend/.env"
    if not env_path.exists():
        return None, False
    token = None
    configured = False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("MINIMAX_TOKEN_PLAN_KEY="):
            val = line.split("=", 1)[1].strip().strip('"')
            if val:
                token = val
                configured = True
    return token, configured


def find_string_field(data: Any, field_names: list[str], depth: int = 0, max_depth: int = 5) -> str:
    """Recursively find a string value from a list of field names."""
    if depth > max_depth or data is None:
        return ""
    if isinstance(data, str):
        return ""
    if not isinstance(data, dict):
        return ""

    d = data
    for fn in field_names:
        if fn in d and isinstance(d[fn], str) and d[fn]:
            return d[fn]

    for key in ("data", "result", "output", "response", "body", "content"):
        if key in d and isinstance(d[key], dict):
            found = find_string_field(d[key], field_names, depth + 1, max_depth)
            if found:
                return found

    return ""


def find_array_field(data: Any, field_name: str, depth: int = 0, max_depth: int = 5) -> list:
    """Recursively find an array field."""
    if depth > max_depth or data is None or not isinstance(data, dict):
        return []
    d = data
    if isinstance(d.get(field_name), list):
        return d[field_name]
    for key in ("data", "result", "output", "response", "body"):
        if key in d and isinstance(d[key], dict):
            found = find_array_field(d[key], field_name, depth + 1, max_depth)
            if found:
                return found
    return []


def find_string_array_field(data: Any, field_name: str, depth: int = 0, max_depth: int = 5) -> list[str]:
    """Recursively find a string array field."""
    arr = find_array_field(data, field_name, depth, max_depth)
    return [x for x in arr if isinstance(x, str) and x]


IMAGE_EXT_PATTERN = re.compile(r"\.(jpg|jpeg|png|webp|gif)$", re.IGNORECASE)


def extract_image_url(data: Any) -> str:
    """Recursively find image URL in response."""
    if data is None:
        return ""
    if not isinstance(data, dict):
        return ""

    d = data

    # Top-level string fields with common names
    for key in ("image_url", "img_url", "imageUrl", "imageURL", "file_url",
                "download_url", "url", "image", "image_file"):
        val = d.get(key)
        if isinstance(val, str) and val:
            if key in ("url", "image"):
                if IMAGE_EXT_PATTERN.search(val):
                    return val
            else:
                return val

    # Recursive search in nested structures
    found = find_string_field(
        data,
        ["image_url", "img_url", "url", "image", "image_file", "file_url",
         "download_url", "imageUrl", "imageURL"],
    )
    if found and IMAGE_EXT_PATTERN.search(found):
        return found

    # Check string arrays
    for arr_key in ("images", "image_urls", "urls"):
        arr = find_string_array_field(data, arr_key)
        if arr:
            for item in arr:
                if IMAGE_EXT_PATTERN.search(item):
                    return item
            # Return first item even without extension check
            return arr[0]

    # Check nested array of objects for url fields
    for arr_key in ("images", "image_urls", "outputs", "results", "data", "items"):
        arr = find_array_field(data, arr_key)
        for item in arr:
            if not isinstance(item, dict):
                continue
            for url_key in ("url", "image_url", "img_url", "file_url", "download_url"):
                val = item.get(url_key)
                if isinstance(val, str) and val and IMAGE_EXT_PATTERN.search(val):
                    return val
            # Fallback: if item itself is a string URL
            if isinstance(item, str) and IMAGE_EXT_PATTERN.search(item):
                return item

    return found or ""


def _extract_error_details(resp: dict) -> dict:
    """Extract structured error details from an API error response."""
    details = {}
    if "error" in resp:
        details["error"] = resp.get("error")
    if "message" in resp:
        details["message"] = resp.get("message")
    base_resp = resp.get("base_resp", {})
    if base_resp:
        details["base_resp.status_code"] = base_resp.get("status_code")
        details["base_resp.status_msg"] = base_resp.get("status_msg")
    return details


def print_result(r: dict) -> None:
    print("\nRunner image smoke result")
    print(f"- base_url: {r['base_url']}")
    print(f"- execute_real: {r['execute_real']}")
    print(f"- confirm_asset_source: {r['confirm_asset_source']}")
    print(f"- health_ok: {r['health_ok']}")
    print(f"- api_key_configured: {r['api_key_configured']}")
    print(f"- minimax_status: {r['minimax_status']}")
    print(f"- templates_loaded: {r['templates_loaded']}")
    print(f"- image_t2i_template: {r['image_t2i_template']}")
    print(f"- image_i2i_template: {r['image_i2i_template']}")
    print(f"- image_t2i_result_type: {r['image_t2i_result_type']}")
    print(f"- image_i2i_result_type: {r['image_i2i_result_type']}")
    print(f"- image_i2i_confirm_asset_source_field: {r['image_i2i_confirm_asset_source_field']}")
    print(f"- image_t2i_ok: {r['image_t2i_ok']}")
    print(f"- image_t2i_image_detected: {r['image_t2i_image_detected']}")
    print(f"- image_t2i_image_url_or_asset: {r['image_t2i_image_url_or_asset']}")
    print(f"- image_i2i_risk_unconfirmed_allowed: {r['image_i2i_risk_unconfirmed_allowed']}")
    print(f"- image_i2i_risk_confirmed_allowed: {r['image_i2i_risk_confirmed_allowed']}")
    print(f"- image_i2i_risk_blocked_reasons: {r['image_i2i_risk_blocked_reasons']}")
    print(f"- image_i2i_risk_required_confirmations: {r['image_i2i_risk_required_confirmations']}")
    print(f"- image_i2i_ok: {r['image_i2i_ok']}")
    print(f"- image_i2i_image_detected: {r['image_i2i_image_detected']}")
    print(f"- image_i2i_image_url_or_asset: {r['image_i2i_image_url_or_asset']}")


def main():
    parser = argparse.ArgumentParser(description="Guided Runner image smoke test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend URL")
    parser.add_argument("--execute-real", action="store_true", help="Actually call MiniMax API (default: dry-run only)")
    parser.add_argument(
        "--confirm-asset-source",
        action="store_true",
        help="Confirm asset source for image-i2i (required with --execute-real for image-i2i invoke)",
    )
    parser.add_argument(
        "--prompt",
        default="一只橘猫坐在窗边，清晨阳光，真实摄影风格",
        help="Prompt for image generation",
    )
    parser.add_argument(
        "--edit-prompt",
        default="保持主体不变，改为电影感光影",
        help="Edit prompt for image-i2i",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="1:1",
        help="Aspect ratio for image-t2i",
    )
    parser.add_argument(
        "--img-url",
        default=None,
        help="Use this image URL directly (skip image-t2i call)",
    )
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url.rstrip("/")

    result = {
        "base_url": BASE_URL,
        "execute_real": args.execute_real,
        "confirm_asset_source": args.confirm_asset_source,
        "health_ok": False,
        "api_key_configured": False,
        "minimax_status": None,
        "templates_loaded": False,
        "image_t2i_template": False,
        "image_i2i_template": False,
        "image_t2i_result_type": None,
        "image_i2i_result_type": None,
        "image_i2i_confirm_asset_source_field": False,
        "image_t2i_ok": None,
        "image_t2i_image_detected": None,
        "image_t2i_image_url_or_asset": None,
        "image_i2i_risk_unconfirmed_allowed": None,
        "image_i2i_risk_confirmed_allowed": None,
        "image_i2i_risk_blocked_reasons": None,
        "image_i2i_risk_required_confirmations": None,
        "image_i2i_ok": None,
        "image_i2i_image_detected": None,
        "image_i2i_image_url_or_asset": None,
    }

    mode = "REAL" if args.execute_real else "DRY"
    token = None
    api_key_configured = False

    # ── 0. Load token for real mode ──────────────────────────────────────────────
    if args.execute_real:
        token, api_key_configured = get_token()
        result["api_key_configured"] = api_key_configured
        if token:
            print(f"[{mode}] token loaded: {_mask_key(token)}")
        else:
            print(f"[{mode}] WARNING: no token found in backend/.env")

    # ── 1. Health check ───────────────────────────────────────────────────────────
    try:
        health_resp = http_get("/api/health", token)
        result["health_ok"] = True
        result["minimax_status"] = health_resp.get("minimax", "unknown")
        result["api_key_configured"] = health_resp.get("api_key_configured", api_key_configured)
        print(f"[{mode}] health ok (minimax={result['minimax_status']}, key_configured={result['api_key_configured']})")
    except Exception as e:
        print(f"[{mode}] health check failed: {e}")
        print_result(result)
        sys.exit(1)

    # ── 2. Load templates ─────────────────────────────────────────────────────────
    try:
        templates_data = http_get("/api/runner/templates", token)
        result["templates_loaded"] = True
    except Exception as e:
        print(f"[{mode}] Failed to load templates: {e}")
        print_result(result)
        sys.exit(1)

    templates = templates_data.get("templates", {})
    result["image_t2i_template"] = "image-t2i" in templates
    result["image_i2i_template"] = "image-i2i" in templates

    t2i_tpl = templates.get("image-t2i", {})
    i2i_tpl = templates.get("image-i2i", {})

    result["image_t2i_result_type"] = t2i_tpl.get("result_type")
    result["image_i2i_result_type"] = i2i_tpl.get("result_type")

    i2i_form_schema = i2i_tpl.get("form_schema", {})
    result["image_i2i_confirm_asset_source_field"] = "confirm_asset_source" in i2i_form_schema

    print(f"[{mode}] templates loaded: {len(templates)}")
    print(f"[{mode}] image-t2i template: {result['image_t2i_template']}")
    print(f"[{mode}] image-i2i template: {result['image_i2i_template']}")
    print(f"[{mode}] image-t2i result_type: {result['image_t2i_result_type']}")
    print(f"[{mode}] image-i2i result_type: {result['image_i2i_result_type']}")
    print(f"[{mode}] image-i2i confirm_asset_source field: {result['image_i2i_confirm_asset_source_field']}")

    if not result["image_t2i_template"]:
        print("[ERROR] image-t2i template not found")
        print_result(result)
        sys.exit(1)
    if not result["image_i2i_template"]:
        print("[ERROR] image-i2i template not found")
        print_result(result)
        sys.exit(1)

    # ── 3. Dry-run: validate payload construction ─────────────────────────────────
    t2i_pld_tpl = t2i_tpl.get("payload_template", {})
    print(f"[{mode}] image-t2i payload_template keys: {list(t2i_pld_tpl.keys())}")

    t2i_built = {
        "model": "image-01",
        "prompt": args.prompt,
        "aspect_ratio": args.aspect_ratio,
    }
    print(f"[{mode}] image-t2i constructed payload: {json.dumps(t2i_built, ensure_ascii=False)}")

    i2i_built = {
        "model": "image-01",
        "prompt": args.edit_prompt,
        "subject_reference": [
            {"type": "character", "image_file": args.img_url or "<img_url>"}
        ],
        "confirm_asset_source": True,
    }
    print(f"[{mode}] image-i2i constructed payload: {json.dumps(i2i_built, ensure_ascii=False)}")

    if not args.execute_real:
        print("[DRY] Dry-run complete — no real API calls made")
        print_result(result)
        sys.exit(0)

    # ── 4. Real: image-t2i ──────────────────────────────────────────────────────
    img_url = args.img_url

    if not img_url:
        print("[REAL] Calling image-t2i...")
        try:
            t2i_resp = http_post(
                "/api/invoke/image-t2i",
                {"payload": t2i_built},
                token,
                timeout=IMAGE_INVOKE_TIMEOUT_SEC,
            )
        except Exception as e:
            print(f"[ERROR] image-t2i invoke failed: {e}")
            print_result(result)
            sys.exit(1)

        if t2i_resp.get("error"):
            err_details = _extract_error_details(t2i_resp)
            print(f"[ERROR] image-t2i returned error:")
            for k, v in err_details.items():
                print(f"  {k}: {v}")
            print_result(result)
            sys.exit(1)

        result["image_t2i_ok"] = True
        img_url = extract_image_url(t2i_resp.get("data", {}))
        result["image_t2i_image_detected"] = bool(img_url)
        result["image_t2i_image_url_or_asset"] = img_url

        if img_url:
            print(f"[REAL] image-t2i ok, image_url extracted: {img_url[:60]}...")
        else:
            data = t2i_resp.get("data", {})
            data_keys = list(data.keys()) if isinstance(data, dict) else type(data)
            print(f"[ERROR] No image URL found in image-t2i response. data keys: {data_keys}")
            print_result(result)
            sys.exit(1)
    else:
        result["image_t2i_ok"] = True
        result["image_t2i_image_detected"] = True
        result["image_t2i_image_url_or_asset"] = img_url
        print(f"[REAL] Using provided img_url: {img_url[:60]}...")

    # ── 5. image-i2i risk-check: unconfirmed (should block) ────────────────────
    unconfirmed_payload = {
        "payload": {
            "model": "image-01",
            "prompt": args.edit_prompt,
            "subject_reference": [
                {"type": "character", "image_file": img_url}
            ],
            "confirm_asset_source": False,
        },
        "confirmations": {},
    }

    print("[REAL] Calling image-i2i risk-check (unconfirmed)...")
    try:
        risk_unconf = http_post("/api/capabilities/image-i2i/risk-check", unconfirmed_payload, token)
    except Exception as e:
        print(f"[ERROR] image-i2i risk-check (unconfirmed) failed: {e}")
        print_result(result)
        sys.exit(1)

    risk_data = risk_unconf.get("data", risk_unconf)
    unconf_allowed = risk_data.get("allowed", False)
    result["image_i2i_risk_unconfirmed_allowed"] = unconf_allowed
    result["image_i2i_risk_blocked_reasons"] = risk_data.get("blocked_reasons", [])
    result["image_i2i_risk_required_confirmations"] = risk_data.get("required_confirmations", [])

    if unconf_allowed:
        print(f"[ERROR] image-i2i risk-check UNCONFIRMED returned allowed=True — RiskGate should block!")
        print(f"  blocked_reasons: {result['image_i2i_risk_blocked_reasons']}")
        print(f"  required_confirmations: {result['image_i2i_risk_required_confirmations']}")
        print_result(result)
        sys.exit(1)

    print(f"[REAL] image-i2i risk-check (unconfirmed) correctly blocked: allowed=False")
    print(f"  required_confirmations: {result['image_i2i_risk_required_confirmations']}")

    # ── 6. image-i2i risk-check: confirmed (should allow) ────────────────────────
    confirmed_payload = {
        "payload": {
            "model": "image-01",
            "prompt": args.edit_prompt,
            "subject_reference": [
                {"type": "character", "image_file": img_url}
            ],
            "confirm_asset_source": True,
        },
        "confirmations": {"confirm_asset_source": True},
    }

    print("[REAL] Calling image-i2i risk-check (confirmed)...")
    try:
        risk_conf = http_post("/api/capabilities/image-i2i/risk-check", confirmed_payload, token)
    except Exception as e:
        print(f"[ERROR] image-i2i risk-check (confirmed) failed: {e}")
        print_result(result)
        sys.exit(1)

    conf_data = risk_conf.get("data", risk_conf)
    conf_allowed = conf_data.get("allowed", False)
    result["image_i2i_risk_confirmed_allowed"] = conf_allowed

    if not conf_allowed:
        print(f"[ERROR] image-i2i risk-check CONFIRMED returned allowed=False — should be allowed!")
        print(f"  blocked_reasons: {conf_data.get('blocked_reasons', [])}")
        print(f"  required_confirmations: {conf_data.get('required_confirmations', [])}")
        print_result(result)
        sys.exit(1)

    print(f"[REAL] image-i2i risk-check (confirmed) allowed=True")

    # ── 7. image-i2i invoke (requires BOTH --execute-real AND --confirm-asset-source) ─
    if not args.confirm_asset_source:
        print("[REAL] Skipping image-i2i invoke: --confirm-asset-source not provided")
        print_result(result)
        sys.exit(0)

    print("[REAL] Calling image-i2i invoke...")
    invoke_payload = {
        "payload": {
            "model": "image-01",
            "prompt": args.edit_prompt,
            "subject_reference": [
                {"type": "character", "image_file": img_url}
            ],
            "confirm_asset_source": True,
        },
        "confirmations": {"confirm_asset_source": True},
    }

    try:
        i2i_resp = http_post("/api/invoke/image-i2i", invoke_payload, token, timeout=IMAGE_INVOKE_TIMEOUT_SEC)
    except Exception as e:
        print(f"[ERROR] image-i2i invoke failed: {e}")
        result["image_i2i_ok"] = False
        print_result(result)
        sys.exit(1)

    if i2i_resp.get("error"):
        err_details = _extract_error_details(i2i_resp)
        print(f"[ERROR] image-i2i returned error:")
        for k, v in err_details.items():
            print(f"  {k}: {v}")
        result["image_i2i_ok"] = False
        print_result(result)
        sys.exit(1)

    result["image_i2i_ok"] = True
    print(f"[REAL] image-i2i ok: True")

    # ── 8. Extract image URL from image-i2i response ─────────────────────────────
    i2i_img_url = extract_image_url(i2i_resp.get("data", {}))
    result["image_i2i_image_detected"] = bool(i2i_img_url)
    result["image_i2i_image_url_or_asset"] = i2i_img_url

    if i2i_img_url:
        print(f"[REAL] image-i2i image detected: {i2i_img_url[:60]}...")
    else:
        data = i2i_resp.get("data", {})
        data_keys = list(data.keys()) if isinstance(data, dict) else type(data)
        print(f"[REAL] image NOT detected in image-i2i response — data keys: {data_keys}")

    print_result(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
