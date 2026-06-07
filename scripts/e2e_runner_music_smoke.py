#!/usr/bin/env python3
"""
Music smoke test for Guided Capability Runner.

Validates the lyrics-gen → music-gen product loop:
  1. Check health
  2. Load runner templates
  3. Verify lyrics-gen and music-gen templates
  4. (With --execute-real) Call lyrics-gen to generate lyrics
  5. (With --execute-real) Verify music-gen risk-check blocks unconfirmed
  6. (With --execute-real) Verify music-gen risk-check allows confirmed
  7. (With --execute-real --confirm-quota) Call music-gen invoke
  8. Verify audio result

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
MUSIC_INVOKE_TIMEOUT_SEC = 300

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


def find_string_field(data: unknown, field_names: list[str], depth: int = 0, max_depth: int = 5) -> str:
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


def extract_lyrics(data: unknown) -> str:
    """Extract lyrics from lyrics-gen response."""
    return find_string_field(
        data,
        ["lyrics", "text", "content", "output", "message", "songLyrics"],
    )


def extract_audio_source(data: unknown, depth: int = 0, max_depth: int = 5) -> tuple[str | None, str]:
    """
    Recursively find audio URL or audio_base64 in response.
    Returns (found_value, kind: 'url' | 'base64' | 'unknown').
    """
    if depth > max_depth or data is None or not isinstance(data, dict):
        return None, "unknown"

    d = data

    # 1. URL type
    for key in ("audio_url", "audio_file", "url", "file_url"):
        if key in d and isinstance(d[key], str) and d[key]:
            val = d[key].lower()
            if any(ext in val for ext in (".mp3", ".wav", ".ogg", ".m4a", ".aac")) or val.startswith("http"):
                return d[key], "url"

    # 2. base64 type
    for key in ("audio_base64", "audio"):
        if key in d and isinstance(d[key], str) and len(d[key]) > 100:
            if d[key].startswith("data:audio/"):
                return d[key], "base64"
            return f"data:audio/mpeg;base64,{d[key]}", "base64"

    # 3. Recurse into containers
    for key in ("data", "result", "output", "response", "body", "content"):
        if key in d and isinstance(d[key], dict):
            found, kind = extract_audio_source(d[key], depth + 1, max_depth)
            if found:
                return found, kind

    # 4. Recurse into arrays
    for val in d.values():
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    found, kind = extract_audio_source(item, depth + 1, max_depth)
                    if found:
                        return found, kind

    return None, "unknown"


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
    print("\nRunner music smoke result")
    print(f"- base_url: {r['base_url']}")
    print(f"- execute_real: {r['execute_real']}")
    print(f"- confirm_quota: {r['confirm_quota']}")
    print(f"- health_ok: {r['health_ok']}")
    print(f"- api_key_configured: {r['api_key_configured']}")
    print(f"- minimax_status: {r['minimax_status']}")
    print(f"- templates_loaded: {r['templates_loaded']}")
    print(f"- lyrics_gen_template: {r['lyrics_gen_template']}")
    print(f"- music_gen_template: {r['music_gen_template']}")
    print(f"- music_gen_result_type: {r['music_gen_result_type']}")
    print(f"- music_gen_confirm_quota_field: {r['music_gen_confirm_quota_field']}")
    print(f"- lyrics_gen_ok: {r['lyrics_gen_ok']}")
    print(f"- lyrics_detected: {r['lyrics_detected']}")
    print(f"- lyrics_length: {r['lyrics_length']}")
    print(f"- music_risk_unconfirmed_allowed: {r['music_risk_unconfirmed_allowed']}")
    print(f"- music_risk_confirmed_allowed: {r['music_risk_confirmed_allowed']}")
    print(f"- music_risk_blocked_reasons: {r['music_risk_blocked_reasons']}")
    print(f"- music_risk_required_confirmations: {r['music_risk_required_confirmations']}")
    print(f"- music_gen_ok: {r['music_gen_ok']}")
    print(f"- audio_detected: {r['audio_detected']}")
    print(f"- audio_kind: {r['audio_kind']}")
    print(f"- audio_url_or_asset: {r['audio_url_or_asset']}")


def main():
    parser = argparse.ArgumentParser(description="Guided Runner music smoke test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend URL")
    parser.add_argument("--execute-real", action="store_true", help="Actually call MiniMax API (default: dry-run only)")
    parser.add_argument(
        "--confirm-quota",
        action="store_true",
        help="Confirm quota consumption for music-gen (required with --execute-real for music-gen invoke)",
    )
    parser.add_argument(
        "--theme",
        default="夏天傍晚的乡村小路",
        help="Theme/prompt for lyrics generation",
    )
    parser.add_argument(
        "--style",
        default="温柔、怀旧、民谣",
        help="Style description for music generation",
    )
    parser.add_argument(
        "--title",
        default="夏日晚风",
        help="Title for lyrics/music generation",
    )
    parser.add_argument(
        "--lyrics",
        default=None,
        help="Use this lyrics directly (skip lyrics-gen call)",
    )
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url.rstrip("/")

    result = {
        "base_url": BASE_URL,
        "execute_real": args.execute_real,
        "confirm_quota": args.confirm_quota,
        "health_ok": False,
        "api_key_configured": False,
        "minimax_status": None,
        "templates_loaded": False,
        "lyrics_gen_template": False,
        "music_gen_template": False,
        "music_gen_result_type": None,
        "music_gen_confirm_quota_field": False,
        "lyrics_gen_ok": None,
        "lyrics_detected": None,
        "lyrics_length": None,
        "music_risk_unconfirmed_allowed": None,
        "music_risk_confirmed_allowed": None,
        "music_risk_blocked_reasons": None,
        "music_risk_required_confirmations": None,
        "music_gen_ok": None,
        "audio_detected": None,
        "audio_kind": None,
        "audio_url_or_asset": None,
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
    result["lyrics_gen_template"] = "lyrics-gen" in templates
    result["music_gen_template"] = "music-gen" in templates

    music_tpl = templates.get("music-gen", {})
    result["music_gen_result_type"] = music_tpl.get("result_type")
    form_schema = music_tpl.get("form_schema", {})
    result["music_gen_confirm_quota_field"] = "confirm_quota" in form_schema

    print(f"[{mode}] templates loaded: {len(templates)}")
    print(f"[{mode}] lyrics-gen template: {result['lyrics_gen_template']}")
    print(f"[{mode}] music-gen template: {result['music_gen_template']}")
    print(f"[{mode}] music-gen result_type: {result['music_gen_result_type']}")
    print(f"[{mode}] music-gen confirm_quota field: {result['music_gen_confirm_quota_field']}")

    if not result["lyrics_gen_template"]:
        print("[ERROR] lyrics-gen template not found")
        print_result(result)
        sys.exit(1)
    if not result["music_gen_template"]:
        print("[ERROR] music-gen template not found")
        print_result(result)
        sys.exit(1)

    # ── 3. Dry-run: validate payload construction ────────────────────────────────
    lyrics_tpl = templates.get("lyrics-gen", {})
    lyrics_pld = lyrics_tpl.get("payload_template", {})

    print(f"[{mode}] lyrics-gen payload_template keys: {list(lyrics_pld.keys())}")

    lyrics_values = {
        "theme": args.theme,
        "title": args.title,
        "style": args.style,
    }

    lyrics_built = {}
    for k, v in lyrics_pld.items():
        if isinstance(v, str):
            lyrics_built[k] = v.replace("{theme}", args.theme).replace("{title}", args.title).replace("{style}", args.style)
        else:
            lyrics_built[k] = v

    print(f"[{mode}] lyrics-gen constructed payload: {json.dumps(lyrics_built, ensure_ascii=False)}")

    music_values = {
        "lyrics": args.lyrics or "<lyrics_placeholder>",
        "prompt": args.style,
        "title": args.title,
        "confirm_quota": "true" if args.confirm_quota else "false",
    }
    music_pld = music_tpl.get("payload_template", {})
    music_built = {}
    for k, v in music_pld.items():
        if isinstance(v, str):
            music_built[k] = v.replace("{lyrics}", args.lyrics or "<lyrics_placeholder>").replace("{prompt}", args.style).replace("{title}", args.title)
        else:
            music_built[k] = v
    print(f"[{mode}] music-gen constructed payload: {json.dumps(music_built, ensure_ascii=False)}")

    if not args.execute_real:
        print("[DRY] Dry-run complete — no real API calls made")
        print_result(result)
        sys.exit(0)

    # ── 4. Real: lyrics-gen ────────────────────────────────────────────────────
    lyrics_text = args.lyrics

    if not lyrics_text:
        print("[REAL] Calling lyrics-gen...")
        try:
            lyrics_resp = http_post(
                "/api/invoke/lyrics-gen",
                {"payload": lyrics_built},
                token,
            )
        except Exception as e:
            print(f"[ERROR] lyrics-gen invoke failed: {e}")
            print_result(result)
            sys.exit(1)

        if lyrics_resp.get("error"):
            err_details = _extract_error_details(lyrics_resp)
            print(f"[ERROR] lyrics-gen returned error:")
            for k, v in err_details.items():
                print(f"  {k}: {v}")
            print_result(result)
            sys.exit(1)

        result["lyrics_gen_ok"] = True
        lyrics_text = extract_lyrics(lyrics_resp.get("data", {}))
        result["lyrics_detected"] = bool(lyrics_text)
        result["lyrics_length"] = len(lyrics_text) if lyrics_text else 0

        if lyrics_text:
            print(f"[REAL] lyrics-gen ok, lyrics extracted ({len(lyrics_text)} chars)")
        else:
            data_keys = list(lyrics_resp.get("data", {}).keys()) if isinstance(lyrics_resp.get("data"), dict) else type(lyrics_resp.get("data"))
            print(f"[ERROR] No lyrics found in lyrics-gen response. data keys: {data_keys}")
            print_result(result)
            sys.exit(1)
    else:
        result["lyrics_gen_ok"] = True
        result["lyrics_detected"] = True
        result["lyrics_length"] = len(lyrics_text)
        print(f"[REAL] Using provided lyrics ({len(lyrics_text)} chars)")

    # ── 5. music-gen risk-check: unconfirmed (should be blocked) ─────────────────
    unconfirmed_payload = {
        "payload": {
            "model": "music-2.6",
            "lyrics": lyrics_text,
            "prompt": args.style,
            "title": args.title,
            "confirm_quota": False,
        },
        "confirmations": {},
    }

    print("[REAL] Calling music-gen risk-check (unconfirmed)...")
    try:
        risk_unconf = http_post("/api/capabilities/music-gen/risk-check", unconfirmed_payload, token)
    except Exception as e:
        print(f"[ERROR] music-gen risk-check (unconfirmed) failed: {e}")
        print_result(result)
        sys.exit(1)

    risk_data = risk_unconf.get("data", risk_unconf)
    unconf_allowed = risk_data.get("allowed", False)
    result["music_risk_unconfirmed_allowed"] = unconf_allowed
    result["music_risk_blocked_reasons"] = risk_data.get("blocked_reasons", [])
    result["music_risk_required_confirmations"] = risk_data.get("required_confirmations", [])

    if unconf_allowed:
        print(f"[ERROR] music-gen risk-check UNCONFIRMED returned allowed=True — RiskGate should block!")
        print(f"  blocked_reasons: {result['music_risk_blocked_reasons']}")
        print(f"  required_confirmations: {result['music_risk_required_confirmations']}")
        print_result(result)
        sys.exit(1)

    print(f"[REAL] music-gen risk-check (unconfirmed) correctly blocked: allowed=False")
    print(f"  required_confirmations: {result['music_risk_required_confirmations']}")

    # ── 6. music-gen risk-check: confirmed (should be allowed) ──────────────────
    confirmed_payload = {
        "payload": {
            "model": "music-2.6",
            "lyrics": lyrics_text,
            "prompt": args.style,
            "title": args.title,
            "confirm_quota": True,
        },
        "confirmations": {"confirm_quota": True},
    }

    print("[REAL] Calling music-gen risk-check (confirmed)...")
    try:
        risk_conf = http_post("/api/capabilities/music-gen/risk-check", confirmed_payload, token)
    except Exception as e:
        print(f"[ERROR] music-gen risk-check (confirmed) failed: {e}")
        print_result(result)
        sys.exit(1)

    conf_data = risk_conf.get("data", risk_conf)
    conf_allowed = conf_data.get("allowed", False)
    result["music_risk_confirmed_allowed"] = conf_allowed

    if not conf_allowed:
        print(f"[ERROR] music-gen risk-check CONFIRMED returned allowed=False — should be allowed!")
        print(f"  blocked_reasons: {conf_data.get('blocked_reasons', [])}")
        print(f"  required_confirmations: {conf_data.get('required_confirmations', [])}")
        print_result(result)
        sys.exit(1)

    print(f"[REAL] music-gen risk-check (confirmed) allowed=True")

    # ── 7. music-gen invoke (only with --confirm-quota) ──────────────────────────
    if not args.confirm_quota:
        print("[REAL] Skipping music-gen invoke: --confirm-quota not provided")
        print_result(result)
        sys.exit(0)

    print("[REAL] Calling music-gen invoke...")
    invoke_payload = {
        "payload": {
            "model": "music-2.6",
            "lyrics": lyrics_text,
            "prompt": args.style,
            "title": args.title,
            "confirm_quota": True,
        },
        "confirmations": {"confirm_quota": True},
    }

    try:
        music_resp = http_post("/api/invoke/music-gen", invoke_payload, token, timeout=MUSIC_INVOKE_TIMEOUT_SEC)
    except Exception as e:
        print(f"[ERROR] music-gen invoke failed: {e}")
        result["music_gen_ok"] = False
        print_result(result)
        sys.exit(1)

    if music_resp.get("error"):
        err_details = _extract_error_details(music_resp)
        print(f"[ERROR] music-gen returned error:")
        for k, v in err_details.items():
            print(f"  {k}: {v}")
        result["music_gen_ok"] = False
        print_result(result)
        sys.exit(1)

    result["music_gen_ok"] = True
    print(f"[REAL] music-gen ok: True")

    # ── 8. Extract audio ─────────────────────────────────────────────────────────
    audio_src, audio_kind = extract_audio_source(music_resp.get("data", {}))
    if audio_src:
        result["audio_detected"] = True
        result["audio_kind"] = audio_kind
        if audio_kind == "base64":
            result["audio_url_or_asset"] = f"<base64 {len(audio_src)} chars>"
            print(f"[REAL] audio_base64 detected ({len(audio_src)} chars)")
        else:
            result["audio_url_or_asset"] = audio_src
            print(f"[REAL] audio_url detected: {audio_src[:60]}...")
    else:
        result["audio_detected"] = False
        result["audio_kind"] = "unknown"
        data = music_resp.get("data", {})
        print(f"[REAL] audio NOT detected — data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")

    print_result(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
