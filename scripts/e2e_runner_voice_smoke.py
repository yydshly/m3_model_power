#!/usr/bin/env python3
"""
Voice smoke test for Guided Capability Runner.

Validates the core voice-list → tts-sync product loop:
  1. Load runner templates
  2. Verify voice-list and tts-sync templates exist
  3. (With --execute-real) Call voice-list to get a voice_id
  4. (With --execute-real) Call tts-sync with that voice_id
  5. Verify audio_url / asset / audio field in response

Safe by default: run without --execute-real for dry-run validation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SEC = 30


def http_post(path: str, body: dict, token: str | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
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


def get_token() -> str | None:
    """Load MINIMAX_TOKEN_PLAN_KEY from backend/.env if present."""
    env_path = _ROOT / "backend/.env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("MINIMAX_TOKEN_PLAN_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def extract_audio_url(data) -> str | None:
    """Recursively find audio URL in response."""
    if isinstance(data, dict):
        for key in ("audio_url", "audio_file", "url", "file_url"):
            if key in data and isinstance(data[key], str) and data[key]:
                val = data[key].lower()
                if any(ext in val for ext in (".mp3", ".wav", ".ogg", ".m4a", ".aac")):
                    return data[key]
        for val in data.values():
            result = extract_audio_url(val)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = extract_audio_url(item)
            if result:
                return result
    return None


def extract_voice_ids(data) -> list[str]:
    """Recursively find voice_id strings in response."""
    results: list[str] = []
    if isinstance(data, dict):
        if "voice_id" in data and isinstance(data["voice_id"], str) and data["voice_id"]:
            results.append(data["voice_id"])
        for val in data.values():
            results.extend(extract_voice_ids(val))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if "voice_id" in item and isinstance(item["voice_id"], str) and item["voice_id"]:
                    results.append(item["voice_id"])
                results.extend(extract_voice_ids(item))
    return results


def resolve_template(val, values, form_schema):
    """Resolve a template value with form field type coercion."""
    if isinstance(val, str):
        exact = re.match(r"^\{(\w+)\}$", val)
        if exact:
            key = exact.group(1)
            v = values.get(key, "")
            field = form_schema.get(key, {})
            vt = field.get("value_type", "")
            if vt == "boolean":
                return v == "true"
            if field.get("type") in ("number", "slider"):
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return v
            return v
        return val  # template literal with other content — pass through
    if isinstance(val, list):
        return [resolve_template(v, values, form_schema) for v in val]
    if isinstance(val, dict):
        return {k: resolve_template(v, values, form_schema) for k, v in val.items()}
    return val


def print_result(r: dict) -> None:
    print("\nRunner voice smoke result")
    print(f"- base_url: {r['base_url']}")
    print(f"- execute_real: {r['execute_real']}")
    print(f"- templates_loaded: {r['templates_loaded']}")
    print(f"- voice_list_template: {r['voice_list_template']}")
    print(f"- tts_sync_template: {r['tts_sync_template']}")
    print(f"- voice_id: {r['voice_id']}")
    print(f"- tts_sync_ok: {r['tts_sync_ok']}")
    print(f"- audio_detected: {r['audio_detected']}")
    print(f"- audio_url_or_asset: {r['audio_url_or_asset']}")


def main():
    parser = argparse.ArgumentParser(description="Guided Runner voice smoke test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend URL")
    parser.add_argument("--execute-real", action="store_true", help="Actually call MiniMax API (default: dry-run only)")
    parser.add_argument(
        "--text",
        default="你好，这是 MiniMax Token Plan 语音合成验证。",
        help="Text for TTS",
    )
    parser.add_argument("--voice-id", default=None, help="Use this voice_id directly (skip voice-list)")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url.rstrip("/")

    result = {
        "base_url": BASE_URL,
        "execute_real": args.execute_real,
        "templates_loaded": False,
        "voice_list_template": False,
        "tts_sync_template": False,
        "voice_id": None,
        "tts_sync_ok": None,
        "audio_detected": None,
        "audio_url_or_asset": None,
    }
    token = get_token() if args.execute_real else None

    # ── 1. Load templates ─────────────────────────────────────────────────────────
    try:
        templates_data = http_get("/api/runner/templates", token)
        result["templates_loaded"] = True
    except Exception as e:
        print(f"[DRY] Failed to load templates: {e}")
        print_result(result)
        sys.exit(1)

    templates = templates_data.get("templates", {})
    result["voice_list_template"] = "voice-list" in templates
    result["tts_sync_template"] = "tts-sync" in templates

    mode = "REAL" if args.execute_real else "DRY"
    print(f"[{mode}] templates loaded: {len(templates)}")
    print(f"[{mode}] voice-list template: {result['voice_list_template']}")
    print(f"[{mode}] tts-sync template: {result['tts_sync_template']}")

    if not result["voice_list_template"]:
        print("[ERROR] voice-list template not found")
        print_result(result)
        sys.exit(1)
    if not result["tts_sync_template"]:
        print("[ERROR] tts-sync template not found")
        print_result(result)
        sys.exit(1)

    # ── 2. Dry-run: validate payload construction ────────────────────────────────
    tts_template = templates.get("tts-sync", {})
    pld_tpl = tts_template.get("payload_template", {})
    form_schema = tts_template.get("form_schema", {})

    print(f"[{mode}] tts-sync payload_template keys: {list(pld_tpl.keys())}")

    test_values = {
        "text": args.text,
        "voice_id": args.voice_id or "test_voice_001",
        "model": "speech-2.8-hd",
        "speed": "1.0",
        "confirm_quota": "false",
    }

    built = resolve_template(pld_tpl, test_values, form_schema)
    print(f"[{mode}] constructed payload: {json.dumps(built, ensure_ascii=False)}")

    if not args.execute_real:
        print("[DRY] Dry-run complete — no real API calls made")
        print_result(result)
        sys.exit(0)

    # ── 3. Real: get voice_id from voice-list ────────────────────────────────────
    if args.voice_id:
        result["voice_id"] = args.voice_id
        print(f"[REAL] Using provided voice_id: {args.voice_id}")
    else:
        print("[REAL] Calling voice-list...")
        try:
            vl_resp = http_post("/api/invoke/voice-list", {"payload": {}}, token)
        except Exception as e:
            print(f"[ERROR] voice-list invoke failed: {e}")
            print_result(result)
            sys.exit(1)

        if vl_resp.get("error"):
            print(f"[ERROR] voice-list returned error: {vl_resp.get('message')}")
            print_result(result)
            sys.exit(1)

        voice_ids = extract_voice_ids(vl_resp.get("data", {}))
        if not voice_ids:
            print("[ERROR] No voice_id found in voice-list response")
            print_result(result)
            sys.exit(1)

        result["voice_id"] = voice_ids[0]
        print(f"[REAL] Got voice_id: {result['voice_id']}")

    # ── 4. Real: call tts-sync ──────────────────────────────────────────────────
    print("[REAL] Calling tts-sync...")
    tts_payload = {
        "payload": {
            "model": "speech-2.8-hd",
            "text": args.text,
            "voice_setting": {
                "voice_id": result["voice_id"],
                "speed": 1.0,
            },
            "confirm_quota": False,
        }
    }

    try:
        tts_resp = http_post("/api/invoke/tts-sync", tts_payload, token)
    except Exception as e:
        print(f"[ERROR] tts-sync invoke failed: {e}")
        result["tts_sync_ok"] = False
        print_result(result)
        sys.exit(1)

    if tts_resp.get("error"):
        print(f"[ERROR] tts-sync returned error: {tts_resp.get('message')}")
        result["tts_sync_ok"] = False
        print_result(result)
        sys.exit(1)

    result["tts_sync_ok"] = True
    print(f"[REAL] tts-sync ok: True")

    # ── 5. Extract audio URL ────────────────────────────────────────────────────
    audio_url = extract_audio_url(tts_resp.get("data", {}))
    if audio_url:
        result["audio_detected"] = True
        result["audio_url_or_asset"] = audio_url
        print(f"[REAL] audio_url detected: {audio_url[:60]}...")
    else:
        result["audio_detected"] = False
        data = tts_resp.get("data", {})
        for key in ("audio_url", "audio_file", "file_url", "url"):
            if key in data and isinstance(data[key], str):
                result["audio_url_or_asset"] = data[key]
                result["audio_detected"] = True
                break
        print(f"[REAL] audio_url NOT detected — data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")

    print_result(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
