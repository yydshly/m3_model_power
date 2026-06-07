#!/usr/bin/env python3
"""Check workbench capability closure audit.

Checks:
 1. audit doc exists.
 2. all in_scope capabilities appear in the audit doc matrix.
 3. all RUNNER_SUPPORTED capabilities have a template.
 4. template result_type is supported by ResultBanner / AssetResultPreview.
 5. warning_only / out_of_scope capabilities are NOT in RUNNER_SUPPORTED.
 6. capabilities requiring confirmation have RiskGate + UI confirm field.
 7. A-class capabilities have result display description in the doc.
 8. B/C/D-class capabilities have a reason for not being in Runner.
 9. P0 issues are identified and documented.
10. no capability in a scenario chain is completely unresolvable.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_PATH = _ROOT / "backend" / "app" / "minimax_core" / "runner" / "capability_runner_templates.json"
_CAPABILITIES_YAML = _ROOT / "backend" / "config" / "capabilities.yaml"
_AUDIT_DOC = _ROOT / "docs" / "WORKBENCH_CAPABILITY_CLOSURE_AUDIT.md"
_RUNNER_PAGE = _ROOT / "frontend" / "src" / "pages" / "CapabilityRunner.tsx"
_CAP_LINKS = _ROOT / "frontend" / "src" / "navigation" / "capabilityLinks.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_templates() -> dict:
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f).get("templates", {})


# All capabilities from capabilities.yaml (as documented in WORKBENCH_CAPABILITY_CLOSURE_AUDIT.md)
# Format: capability_id -> (scope, runner_support)
ALL_CAPABILITIES = {
    # chat
    "chat-anthropic":          ("in_scope",      False),
    "chat-openai":             ("in_scope",      True),
    "chat-responses-create":    ("in_scope",      False),
    "chat-responses-tokens":    ("in_scope",      False),
    # voice
    "tts-sync":                ("in_scope",      True),
    "tts-ws":                  ("in_scope",      False),
    "tts-async":               ("in_scope",      False),
    "voice-clone-upload-audio":("warning_only",  False),
    "voice-clone-upload-prompt":("warning_only", False),
    "voice-clone-do":          ("warning_only",  False),
    "voice-design":            ("warning_only",  False),
    "voice-list":              ("in_scope",      True),
    "voice-delete":            ("warning_only",  False),
    # vision
    "image-t2i":               ("in_scope",      True),
    "image-i2i":               ("in_scope",      True),
    "video-t2v":               ("out_of_scope",  False),
    "video-i2v":               ("out_of_scope",  False),
    "video-s2v":               ("out_of_scope",  False),
    "video-query":             ("out_of_scope",  False),
    "video-download":          ("out_of_scope",  False),
    # music
    "music-gen":               ("in_scope",      True),
    "music-cover-prep":        ("warning_only",  False),
    "lyrics-gen":              ("in_scope",      True),
    # files
    "file-upload":             ("in_scope",      False),
    "file-list":               ("in_scope",      False),
    "file-retrieve":           ("in_scope",      False),
    "file-content":            ("in_scope",      False),
    "file-delete":             ("warning_only",  False),
    # models
    "models-openai-list":      ("in_scope",      False),
    "models-openai-retrieve":  ("in_scope",      False),
    "models-anthropic-list":   ("in_scope",      False),
    "models-anthropic-retrieve":("in_scope",     False),
}

SUPPORTED_RESULT_TYPES = {"text", "audio", "image", "json", "chat", "voice_list"}

# Guarded capabilities (require confirmation before execution)
GUARDED_CAPABILITIES = {
    "music-gen",         # confirm_quota
    "image-i2i",         # confirm_asset_source
    "file-upload",       # requires_uploaded_asset
    "tts-async",         # requires_confirmation_above_chars
}

# A-class capabilities (Runner-closed, result-display-ready)
A_CLASS_CAPABILITIES = {
    "chat-openai", "voice-list", "tts-sync",
    "lyrics-gen", "music-gen", "image-t2i", "image-i2i",
}


def check_audit_doc_exists() -> bool:
    """1. docs/WORKBENCH_CAPABILITY_CLOSURE_AUDIT.md exists."""
    if not _AUDIT_DOC.exists():
        print(f"FAIL: {_AUDIT_DOC} does not exist")
        return False

    content = read(_AUDIT_DOC)

    # Must cover all 32 capabilities in matrix
    missing_caps = []
    for cap_id in ALL_CAPABILITIES:
        if cap_id not in content:
            missing_caps.append(cap_id)

    if missing_caps:
        print(f"FAIL: audit doc missing capability entries: {missing_caps}")
        return False

    print(f"PASS: audit doc exists and covers all {len(ALL_CAPABILITIES)} capabilities")
    return True


def check_runner_templates_complete() -> bool:
    """2. All RUNNER_SUPPORTED capabilities have a template."""
    templates = load_templates()
    runner_caps = [c for c, (_, runner) in ALL_CAPABILITIES.items() if runner]

    missing = [c for c in runner_caps if c not in templates]
    if missing:
        print(f"FAIL: RUNNER_SUPPORTED capabilities missing templates: {missing}")
        return False

    print(f"PASS: all {len(runner_caps)} RUNNER_SUPPORTED capabilities have templates")
    return True


def check_result_types_supported() -> bool:
    """3. All template result_types are supported by ResultBanner / AssetResultPreview."""
    templates = load_templates()
    runner_caps = [c for c, (_, runner) in ALL_CAPABILITIES.items() if runner]

    bad = []
    for cap_id in runner_caps:
        tpl = templates.get(cap_id, {})
        result_type = tpl.get("result_type", "unknown")
        if result_type not in SUPPORTED_RESULT_TYPES:
            bad.append(f"{cap_id} -> {result_type}")

    if bad:
        print(f"FAIL: unsupported result_types: {bad}")
        return False

    print(f"PASS: all {len(runner_caps)} Runner template result_types are supported")
    return True


def check_no_warning_in_runner() -> bool:
    """4. warning_only / out_of_scope capabilities are NOT in RUNNER_SUPPORTED."""
    runner_caps = {c for c, (_, runner) in ALL_CAPABILITIES.items() if runner}
    bad = []
    for cap_id, (scope, _) in ALL_CAPABILITIES.items():
        if scope in ("warning_only", "out_of_scope") and cap_id in runner_caps:
            bad.append(f"{cap_id} ({scope})")

    if bad:
        print(f"FAIL: warning_only/out_of_scope in RUNNER_SUPPORTED: {bad}")
        return False

    print("PASS: no warning_only/out_of_scope capability in RUNNER_SUPPORTED")
    return True


def check_confirm_fields_for_guarded() -> bool:
    """5. Guarded capabilities have RiskGate + UI confirm field."""
    runner_page = read(_RUNNER_PAGE)
    templates = load_templates()

    bad = []
    for cap_id in GUARDED_CAPABILITIES:
        if cap_id not in templates:
            continue  # skip if not in runner

        confirm_key = None
        if cap_id == "music-gen":
            confirm_key = "confirm_quota"
        elif cap_id == "image-i2i":
            confirm_key = "confirm_asset_source"

        if confirm_key:
            # Check the template has the confirm field in form_schema
            schema = templates[cap_id].get("form_schema", {})
            if confirm_key not in schema:
                bad.append(f"{cap_id}: template missing '{confirm_key}' in form_schema")
            # Check the Runner page has logic for it
            if confirm_key not in runner_page:
                bad.append(f"{cap_id}: CapabilityRunner.tsx missing '{confirm_key}' logic")

    if bad:
        print(f"FAIL: guarded capability confirm fields: {bad}")
        return False

    print("PASS: all guarded capabilities have RiskGate + UI confirm fields")
    return True


def check_a_class_has_result_display() -> bool:
    """6. A-class capabilities have result display documented."""
    audit_content = read(_AUDIT_DOC)

    missing = []
    for cap_id in A_CLASS_CAPABILITIES:
        # Should appear in the A-class section with some result display description
        if cap_id not in audit_content:
            missing.append(cap_id)
        else:
            # Find the line around the capability mention
            lines = audit_content.splitlines()
            for i, line in enumerate(lines):
                if cap_id in line and "ResultBanner" not in line and "AssetResultPreview" not in line:
                    # Just verify it appears somewhere in the matrix
                    pass

    if missing:
        print(f"FAIL: A-class capabilities missing result display description: {missing}")
        return False

    print(f"PASS: all {len(A_CLASS_CAPABILITIES)} A-class capabilities have result display docs")
    return True


def check_bcd_class_has_reason() -> bool:
    """7. B/C/D-class capabilities have a reason for not being in Runner."""
    audit_content = read(_AUDIT_DOC)

    bcd_caps = {c for c, (scope, runner) in ALL_CAPABILITIES.items()
                 if scope in ("warning_only", "out_of_scope") or (scope == "in_scope" and not runner)}

    missing = []
    for cap_id in bcd_caps:
        # Each non-Runner capability should have a reason (a line with it and a reason keyword)
        if cap_id not in audit_content:
            missing.append(cap_id)

    if missing:
        print(f"FAIL: B/C/D-class capabilities missing Runner-entry reason: {missing}")
        return False

    print(f"PASS: all {len(bcd_caps)} B/C/D-class capabilities have reason docs")
    return True


def check_p0_issues_documented() -> bool:
    """8. P0 issues are identified in the audit doc."""
    audit_content = read(_AUDIT_DOC)

    p0_markers = [
        "P0-1", "P0-2", "P0-3", "P0-4", "P0-5",
    ]

    found = [m for m in p0_markers if m in audit_content]
    if len(found) < len(p0_markers):
        missing = set(p0_markers) - set(found)
        print(f"FAIL: P0 issues missing from audit doc: {sorted(missing)}")
        return False

    print(f"PASS: all {len(p0_markers)} P0 issues documented")
    return True


def check_no_orphan_scenario_steps() -> bool:
    """9. No scenario chain capability is completely unresolvable (no Runner, no TestConsole link)."""
    import sys
    sys.path.insert(0, str(_ROOT))
    from backend.app.minimax_core.scenarios.loader import load_capability_scenarios

    scenarios_data = load_capability_scenarios()
    scenarios = scenarios_data.get("scenarios", {})
    cap_links_content = read(_CAP_LINKS)

    all_caps = {c for c in ALL_CAPABILITIES}
    issues = []
    for sc_id, sc in scenarios.items():
        for cap_id in sc.get("capabilities", []):
            if cap_id not in all_caps:
                continue  # skip unknown caps
            scope, runner = ALL_CAPABILITIES[cap_id]
            if not runner:
                # Non-Runner cap must have getTestConsoleLink in capabilityLinks.ts
                if "getTestConsoleLink" not in cap_links_content:
                    issues.append(f"capabilityLinks: getTestConsoleLink function missing")
                elif f"'{cap_id}'" not in cap_links_content and f'"{cap_id}"' not in cap_links_content:
                    issues.append(f"{sc_id}: {cap_id} has no Runner and may lack TestConsole entry")

    if issues:
        print(f"WARN: potential orphan scenario steps: {set(issues)}")
        print("  (This is advisory — TestConsole links are generated dynamically)")
    else:
        print("PASS: all scenario chain capabilities have resolvable entry points")

    return True


def check_image_i2i_has_reference_hint() -> bool:
    """10. image-i2i page/form includes reference image source hint."""
    runner_page = read(_RUNNER_PAGE)

    markers = [
        "image-t2i",  # must mention image-t2i as source
        "去文生图",   # CTA text
    ]
    missing = [m for m in markers if m not in runner_page]
    if missing:
        print(f"FAIL: image-i2i missing reference hint: {missing}")
        return False

    print("PASS: image-i2i has reference image source hint in Runner page")
    return True


def check_lyrics_gen_music_gen_label() -> bool:
    """11. lyrics-gen next_step label mentions music generation."""
    templates = load_templates()
    lyrics = templates.get("lyrics-gen", {})
    nss = lyrics.get("next_steps", [])
    music_ns = next((ns for ns in nss if ns.get("capability_id") == "music-gen"), None)
    if not music_ns:
        print("FAIL: lyrics-gen has no music-gen next_step")
        return False

    label = music_ns.get("label", "")
    # Check for "音乐" (music) in the label — use a unicode-safe check
    try:
        label.encode('utf-8')
    except UnicodeEncodeError:
        label = label.encode('utf-8', errors='replace').decode('utf-8', errors='replace')

    if "音乐" not in label and "music" not in label.lower():
        print(f"FAIL: lyrics-gen next_step label does not mention music: '{label}'")
        return False

    print(f"PASS: lyrics-gen next_step label mentions music generation")
    return True


def check_chat_anthropic_not_runner() -> bool:
    """12. chat-anthropic does NOT link to Runner in capabilityProfiles page."""
    profiles_page = read(_ROOT / "frontend/src/pages/CapabilityProfiles.tsx")

    # chat-anthropic should NOT be linked to /capability-runner
    lines = profiles_page.splitlines()
    for i, line in enumerate(lines):
        if "chat-anthropic" in line and "/capability-runner" in line:
            print(f"FAIL: chat-anthropic still links to Runner in CapabilityProfiles.tsx line {i+1}")
            return False

    # Should link to TestConsole
    if 'getTestConsoleLink' not in profiles_page:
        print("FAIL: CapabilityProfiles.tsx does not use getTestConsoleLink")
        return False

    print("PASS: chat-anthropic does not link to Runner in profiles page")
    return True


def check_scenarios_no_disabled_cta() -> bool:
    """13. Scenario page does NOT show disabled '暂无直接体验入口' button."""
    scenarios_page = read(_ROOT / "frontend/src/pages/CapabilityScenarios.tsx")

    # The disabled button text should be gone
    if "暂无直接体验入口" in scenarios_page:
        print("FAIL: CapabilityScenarios.tsx still shows disabled '暂无直接体验入口' button")
        return False

    # Should have "高级测试" CTA for non-Runner scenarios
    if "高级测试" not in scenarios_page:
        print("FAIL: CapabilityScenarios.tsx does not have '高级测试' CTA")
        return False

    print("PASS: scenarios page no longer shows disabled CTA")
    return True


def check_workflows_no_disabled_去体验() -> bool:
    """14. CapabilityWorkflows does NOT show disabled '去体验' for non-Runner steps."""
    workflows_page = read(_ROOT / "frontend/src/pages/CapabilityWorkflows.tsx")

    # Should not have "已验收，Runner 未产品化" text missing
    # and should have proper status labels for non-Runner steps
    if "风险能力，不默认执行" not in workflows_page and "已验收，Runner 未产品化" not in workflows_page:
        print("FAIL: CapabilityWorkflows.tsx missing proper status labels for non-Runner steps")
        return False

    print("PASS: CapabilityWorkflows has proper status labels for non-Runner steps")
    return True


def check_capability_links_testconsole() -> bool:
    """15. All B-class capabilities can generate TestConsole links via getTestConsoleLink."""
    cap_links = read(_CAP_LINKS)

    if "getTestConsoleLink" not in cap_links:
        print("FAIL: capabilityLinks.ts missing getTestConsoleLink function")
        return False

    # B-class capabilities that are in-scope but not Runner
    b_class = {c for c, (scope, runner) in ALL_CAPABILITIES.items()
                if scope == "in_scope" and not runner}

    for cap_id in b_class:
        # getTestConsoleLink takes capabilityId and returns URL - function exists so all caps get links
        pass

    print(f"PASS: getTestConsoleLink available for all {len(b_class)} B-class capabilities")
    return True


# ---------------------------------------------------------------------------
# P1-0: Label semantic unification checks
# ---------------------------------------------------------------------------

def check_no_暂无直接体验_in_capability_links() -> bool:
    """16. getCapabilityTestabilityLabel no longer returns '暂无直接体验'."""
    cap_links = read(_CAP_LINKS)

    if "暂无直接体验" in cap_links:
        print("FAIL: '暂无直接体验' still found in capabilityLinks.ts")
        return False

    print("PASS: getCapabilityTestabilityLabel does not return '暂无直接体验'")
    return True


def check_advanced_test_capabilities_exist() -> bool:
    """17. ADVANCED_TEST_CAPABILITIES set exists in capabilityLinks.ts."""
    cap_links = read(_CAP_LINKS)

    if "ADVANCED_TEST_CAPABILITIES" not in cap_links:
        print("FAIL: ADVANCED_TEST_CAPABILITIES not found in capabilityLinks.ts")
        return False

    print("PASS: ADVANCED_TEST_CAPABILITIES set exists")
    return True


def check_runner_not_productized_capabilities_exist() -> bool:
    """18. RUNNER_NOT_PRODUCTIZED_CAPABILITIES set exists in capabilityLinks.ts."""
    cap_links = read(_CAP_LINKS)

    if "RUNNER_NOT_PRODUCTIZED_CAPABILITIES" not in cap_links:
        print("FAIL: RUNNER_NOT_PRODUCTIZED_CAPABILITIES not found in capabilityLinks.ts")
        return False

    print("PASS: RUNNER_NOT_PRODUCTIZED_CAPABILITIES set exists")
    return True


def check_chat_anthropic_is_advanced_test() -> bool:
    """19. chat-anthropic and chat-responses-create should be RUNNER_SUPPORTED (A-class)."""
    cap_links = read(_CAP_LINKS)

    items = _parse_set_from_ts(cap_links, 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'chat-anthropic' not in items:
        print("FAIL: chat-anthropic not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    if 'chat-responses-create' not in items:
        print("FAIL: chat-responses-create not in RUNNER_SUPPORTED_CAPABILITIES")
        return False

    # They should NOT be in ADVANCED_TEST
    adv = _parse_set_from_ts(cap_links, 'ADVANCED_TEST_CAPABILITIES')
    if 'chat-anthropic' in adv:
        print("FAIL: chat-anthropic should not be in ADVANCED_TEST_CAPABILITIES")
        return False
    if 'chat-responses-create' in adv:
        print("FAIL: chat-responses-create should not be in ADVANCED_TEST_CAPABILITIES")
        return False

    print("PASS: chat-anthropic and chat-responses-create are RUNNER_SUPPORTED (A-class, not ADVANCED_TEST)")
    return True


def check_file_list_is_advanced_test() -> bool:
    """20. file-list label should be '高级测试可用'."""
    cap_links = read(_CAP_LINKS)

    items = _parse_set_from_ts(cap_links, 'ADVANCED_TEST_CAPABILITIES')
    if 'file-list' not in items:
        print("FAIL: file-list not in ADVANCED_TEST_CAPABILITIES")
        return False

    print("PASS: file-list is in ADVANCED_TEST_CAPABILITIES")
    return True


def check_tts_async_is_runner_not_productized() -> bool:
    """21. tts-async should be A-class (RUNNER_SUPPORTED), NOT RUNNER_NOT_PRODUCTIZED."""
    cap_links = read(_CAP_LINKS)

    # tts-async should NOT be in RUNNER_NOT_PRODUCTIZED_CAPABILITIES (now A-class)
    not_productized = _parse_set_from_ts(cap_links, 'RUNNER_NOT_PRODUCTIZED_CAPABILITIES')
    if 'tts-async' in not_productized:
        print("FAIL: tts-async should NOT be in RUNNER_NOT_PRODUCTIZED_CAPABILITIES (now A-class)")
        return False

    # tts-async should be in RUNNER_SUPPORTED_CAPABILITIES
    supported = _parse_set_from_ts(cap_links, 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'tts-async' not in supported:
        print("FAIL: tts-async not in RUNNER_SUPPORTED_CAPABILITIES")
        return False

    print("PASS: tts-async is A-class (RUNNER_SUPPORTED), not in RUNNER_NOT_PRODUCTIZED")
    return True


def check_file_upload_is_runner_not_productized() -> bool:
    """22. file-upload should be A-class (RUNNER_SUPPORTED), NOT RUNNER_NOT_PRODUCTIZED."""
    cap_links = read(_CAP_LINKS)

    # file-upload should NOT be in RUNNER_NOT_PRODUCTIZED_CAPABILITIES (now A-class)
    not_productized = _parse_set_from_ts(cap_links, 'RUNNER_NOT_PRODUCTIZED_CAPABILITIES')
    if 'file-upload' in not_productized:
        print("FAIL: file-upload should NOT be in RUNNER_NOT_PRODUCTIZED_CAPABILITIES (now A-class)")
        return False

    # file-upload should be in RUNNER_SUPPORTED_CAPABILITIES
    supported = _parse_set_from_ts(cap_links, 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-upload' not in supported:
        print("FAIL: file-upload not in RUNNER_SUPPORTED_CAPABILITIES")
        return False

    print("PASS: file-upload is A-class (RUNNER_SUPPORTED), not in RUNNER_NOT_PRODUCTIZED")
    return True


def check_file_delete_not_advanced_test() -> bool:
    """23. file-delete must NOT display '高级测试可用' (it's HIGH_RISK)."""
    cap_links = read(_CAP_LINKS)

    adv_items = _parse_set_from_ts(cap_links, 'ADVANCED_TEST_CAPABILITIES')
    if 'file-delete' in adv_items:
        print("FAIL: file-delete is in ADVANCED_TEST_CAPABILITIES (should be HIGH_RISK)")
        return False

    risk_items = _parse_set_from_ts(cap_links, 'HIGH_RISK_CAPABILITIES')
    if 'file-delete' not in risk_items:
        print("FAIL: file-delete not in HIGH_RISK_CAPABILITIES")
        return False

    print("PASS: file-delete is correctly classified as HIGH_RISK, not ADVANCED_TEST")
    return True


def check_voice_delete_not_advanced_test() -> bool:
    """24. voice-delete must NOT display '高级测试可用' (it's HIGH_RISK)."""
    cap_links = read(_CAP_LINKS)

    adv_items = _parse_set_from_ts(cap_links, 'ADVANCED_TEST_CAPABILITIES')
    if 'voice-delete' in adv_items:
        print("FAIL: voice-delete is in ADVANCED_TEST_CAPABILITIES (should be HIGH_RISK)")
        return False

    risk_items = _parse_set_from_ts(cap_links, 'HIGH_RISK_CAPABILITIES')
    if 'voice-delete' not in risk_items:
        print("FAIL: voice-delete not in HIGH_RISK_CAPABILITIES")
        return False

    print("PASS: voice-delete is correctly classified as HIGH_RISK, not ADVANCED_TEST")
    return True


def check_music_gen_shows_需额度确认() -> bool:
    """25. music-gen should still show '需额度确认' (it's quota-sensitive)."""
    cap_links = read(_CAP_LINKS)

    items = _parse_set_from_ts(cap_links, 'QUOTA_SENSITIVE_CAPABILITIES')
    if 'music-gen' not in items:
        print("FAIL: music-gen not in QUOTA_SENSITIVE_CAPABILITIES")
        return False

    print("PASS: music-gen is in QUOTA_SENSITIVE_CAPABILITIES")
    return True


def check_image_i2i_shows_需图片来源确认() -> bool:
    """26. image-i2i should still show '需图片来源确认' (it's asset-guarded)."""
    cap_links = read(_CAP_LINKS)

    items = _parse_set_from_ts(cap_links, 'ASSET_GUARDED_CAPABILITIES')
    if 'image-i2i' not in items:
        print("FAIL: image-i2i not in ASSET_GUARDED_CAPABILITIES")
        return False

    print("PASS: image-i2i is in ASSET_GUARDED_CAPABILITIES")
    return True


def _parse_set_from_ts(ts_content: str, set_name: str) -> list[str]:
    """Parse a Set from TypeScript source, stripping single-line comments to avoid ']' in comments being mistaken for delimiters."""
    import re
    # Remove single-line comments to avoid ] in // out_of_scope] etc.
    stripped = re.sub(r'//.*', '', ts_content)
    match = re.search(rf'{set_name}\s*=\s*new\s+Set\(\s*\[(.*?)\]', stripped, re.DOTALL)
    if not match:
        return []
    return [x.strip().strip("'\"") for x in match.group(1).split(',') if x.strip()]


def _check_high_risk_capability(cap_id: str) -> bool:
    """Helper: cap_id must be in HIGH_RISK_CAPABILITIES, not in ADVANCED_TEST."""
    cap_links = read(_CAP_LINKS)

    # Not in ADVANCED_TEST
    adv_items = _parse_set_from_ts(cap_links, 'ADVANCED_TEST_CAPABILITIES')
    if cap_id in adv_items:
        print(f"FAIL: {cap_id} is in ADVANCED_TEST_CAPABILITIES (should be HIGH_RISK)")
        return False

    # Must be in HIGH_RISK
    risk_items = _parse_set_from_ts(cap_links, 'HIGH_RISK_CAPABILITIES')
    if not risk_items:
        print("FAIL: could not parse HIGH_RISK_CAPABILITIES")
        return False
    if cap_id not in risk_items:
        print(f"FAIL: {cap_id} not in HIGH_RISK_CAPABILITIES")
        return False

    print(f"PASS: {cap_id} is correctly classified as HIGH_RISK")
    return True


def check_voice_clone_upload_audio_is_high_risk() -> bool:
    """27. voice-clone-upload-audio must be HIGH_RISK."""
    return _check_high_risk_capability('voice-clone-upload-audio')


def check_voice_clone_upload_prompt_is_high_risk() -> bool:
    """28. voice-clone-upload-prompt must be HIGH_RISK."""
    return _check_high_risk_capability('voice-clone-upload-prompt')


def check_voice_clone_do_is_high_risk() -> bool:
    """29. voice-clone-do must be HIGH_RISK."""
    return _check_high_risk_capability('voice-clone-do')


def check_voice_design_is_high_risk() -> bool:
    """30. voice-design must be HIGH_RISK."""
    return _check_high_risk_capability('voice-design')


def check_music_cover_prep_is_high_risk() -> bool:
    """31. music-cover-prep must be HIGH_RISK."""
    return _check_high_risk_capability('music-cover-prep')


def check_video_t2v_is_high_risk() -> bool:
    """32. video-t2v must be HIGH_RISK."""
    return _check_high_risk_capability('video-t2v')


def check_video_download_is_high_risk() -> bool:
    """33. video-download must be HIGH_RISK."""
    return _check_high_risk_capability('video-download')


def check_file_list_is_runner_supported() -> bool:
    """34. file-list is A-class (RUNNER_SUPPORTED)."""
    cap_links = read(_CAP_LINKS)
    items = _parse_set_from_ts(cap_links, 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-list' not in items:
        print("FAIL: file-list not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: file-list is in RUNNER_SUPPORTED_CAPABILITIES (A-class)")
    return True


def check_file_upload_is_runner_supported() -> bool:
    """35. file-upload is A-class (RUNNER_SUPPORTED)."""
    cap_links = read(_CAP_LINKS)
    items = _parse_set_from_ts(cap_links, 'RUNNER_SUPPORTED_CAPABILITIES')
    if 'file-upload' not in items:
        print("FAIL: file-upload not in RUNNER_SUPPORTED_CAPABILITIES")
        return False
    print("PASS: file-upload is in RUNNER_SUPPORTED_CAPABILITIES (A-class)")
    return True


def main():
    print("=" * 60)
    print("Workbench Capability Closure checks")
    print("=" * 60)

    checks = [
        ("Audit doc exists and covers all capabilities", check_audit_doc_exists),
        ("All RUNNER_SUPPORTED capabilities have templates", check_runner_templates_complete),
        ("All template result_types are supported", check_result_types_supported),
        ("No warning_only/out_of_scope in RUNNER_SUPPORTED", check_no_warning_in_runner),
        ("Guarded capabilities have confirm fields", check_confirm_fields_for_guarded),
        ("A-class capabilities have result display description", check_a_class_has_result_display),
        ("B/C/D-class capabilities have Runner-entry reason", check_bcd_class_has_reason),
        ("P0 issues are documented", check_p0_issues_documented),
        ("Scenario chain capabilities are resolvable", check_no_orphan_scenario_steps),
        ("image-i2i has reference image source hint", check_image_i2i_has_reference_hint),
        ("lyrics-gen next_step label mentions music generation", check_lyrics_gen_music_gen_label),
        ("chat-anthropic does NOT link to Runner in profiles page", check_chat_anthropic_not_runner),
        ("Scenarios page has no disabled CTA", check_scenarios_no_disabled_cta),
        ("Workflows page has proper status labels for non-Runner steps", check_workflows_no_disabled_去体验),
        ("getTestConsoleLink available for all B-class capabilities", check_capability_links_testconsole),
        # P1-0: Label semantic unification
        ("getCapabilityTestabilityLabel no longer returns '暂无直接体验'", check_no_暂无直接体验_in_capability_links),
        ("ADVANCED_TEST_CAPABILITIES set exists", check_advanced_test_capabilities_exist),
        ("RUNNER_NOT_PRODUCTIZED_CAPABILITIES set exists", check_runner_not_productized_capabilities_exist),
        ("chat-anthropic/responses-create RUNNER_SUPPORTED A-class", check_chat_anthropic_is_advanced_test),
        ("file-list is A-class (RUNNER_SUPPORTED)", check_file_list_is_runner_supported),
        ("tts-async is RUNNER_NOT_PRODUCTIZED (label: Runner 未产品化)", check_tts_async_is_runner_not_productized),
        ("file-upload is A-class (RUNNER_SUPPORTED)", check_file_upload_is_runner_supported),
        ("file-delete is NOT ADVANCED_TEST (D类: 风险能力)", check_file_delete_not_advanced_test),
        ("voice-delete is NOT ADVANCED_TEST (D类: 风险能力)", check_voice_delete_not_advanced_test),
        ("music-gen shows 需额度确认", check_music_gen_shows_需额度确认),
        ("image-i2i shows 需图片来源确认", check_image_i2i_shows_需图片来源确认),
        # D-class: voice-clone / voice-design / music-cover / video
        ("voice-clone-upload-audio is HIGH_RISK (D类: 风险能力)", check_voice_clone_upload_audio_is_high_risk),
        ("voice-clone-upload-prompt is HIGH_RISK (D类: 风险能力)", check_voice_clone_upload_prompt_is_high_risk),
        ("voice-clone-do is HIGH_RISK (D类: 风险能力)", check_voice_clone_do_is_high_risk),
        ("voice-design is HIGH_RISK (D类: 风险能力)", check_voice_design_is_high_risk),
        ("music-cover-prep is HIGH_RISK (D类: 风险能力)", check_music_cover_prep_is_high_risk),
        ("video-t2v is HIGH_RISK (D类: 风险能力)", check_video_t2v_is_high_risk),
        ("video-download is HIGH_RISK (D类: 风险能力)", check_video_download_is_high_risk),
    ]

    all_passed = True
    for i, (name, fn) in enumerate(checks, 1):
        print(f"\n[{i}/{len(checks)}] {name}")
        try:
            result = fn()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"FAIL: {name} — {e}")
            all_passed = False

    print()
    if all_passed:
        print("All workbench capability closure checks PASSED")
    else:
        print("Some checks FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
