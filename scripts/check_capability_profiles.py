#!/usr/bin/env python3
"""验证 capability_profiles.json / capability_workflows.json / capability_scenarios.json 的结构完整性和引用一致性。"""
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from backend.app.minimax_core.registry.loader import get_capability_registry

# ── 常量 ────────────────────────────────────────────────────────────────────
PROFILES_FILE = _root / "backend/app/minimax_core/profiles/capability_profiles.json"
WORKFLOWS_FILE = _root / "backend/app/minimax_core/workflows/capability_workflows.json"
SCENARIOS_FILE = _root / "backend/app/minimax_core/scenarios/capability_scenarios.json"

EXPECTED_PROFILES = {"chat", "voice", "vision", "music", "assets", "models"}
EXPECTED_WORKFLOWS = {"voice_generation", "music_creation", "image_creation", "file_knowledge", "chat_model_comparison"}
EXPECTED_SCENARIOS = {
    "short_video_voiceover", "emotion_dialog_voice", "emotion_mv_music",
    "image_cover_generation", "image_reference_variation", "file_knowledge_entry",
    "chat_model_comparison", "agent_api_integration"
}

PROFILE_REQUIRED_FIELDS = [
    "family", "label", "user_summary", "token_plan_status", "api_status",
    "verified_capabilities", "direct_testable_capabilities", "guarded_capabilities",
    "not_default_executable", "model_notes", "capability_modes", "key_parameters",
    "outputs", "recommended_scenarios", "recommended_workflows", "risk_notes", "product_usage"
]

WORKFLOW_REQUIRED_FIELDS = [
    "id", "label", "family", "summary", "steps", "default_inputs",
    "risk_policy", "expected_outputs", "product_usage"
]

SCENARIO_REQUIRED_FIELDS = [
    "id", "label", "summary", "recommended_for", "capability_family",
    "workflow_id", "capabilities", "recommended_models", "risk_level",
    "expected_output", "default_inputs", "cta"
]

VALID_SOURCES = {"official_docs", "token_plan_verified", "local_config", "historical_compat", "risk_warning"}
VALID_RECOMMENDATION_LEVELS = {
    "official_primary", "official_current", "verified_stable",
    "low_latency", "high_quality", "quota_friendly",
    "compatible", "guarded", "free_tier", "not_default", "not_applicable"
}
MODEL_NOTES_REQUIRED_FIELDS = ["model", "label", "source", "recommendation_level", "best_for", "notes"]

errors: list[str] = []
warnings: list[str] = []


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        errors.append(f"FAIL: cannot load {path.name}: {e}")
        sys.exit(1)


# ── 加载数据 ────────────────────────────────────────────────────────────────
profiles_data = load_json(PROFILES_FILE)
workflows_data = load_json(WORKFLOWS_FILE)
scenarios_data = load_json(SCENARIOS_FILE)

reg = get_capability_registry()
all_cap_ids = {cap.id for cap in reg.all()}

# ── 1. 校验 profiles ─────────────────────────────────────────────────────────
print("Capability Profile checks")

profiles = profiles_data.get("profiles", {})
if "schema_version" not in profiles_data:
    errors.append("profiles: missing 'schema_version'")
if not isinstance(profiles, dict):
    errors.append("profiles: 'profiles' must be a dict")
    profiles = {}

# 家族数量
if set(profiles.keys()) != EXPECTED_PROFILES:
    missing = EXPECTED_PROFILES - set(profiles.keys())
    extra = set(profiles.keys()) - EXPECTED_PROFILES
    if missing:
        errors.append(f"profiles: missing families: {sorted(missing)}")
    if extra:
        errors.append(f"profiles: unexpected families: {sorted(extra)}")

for key, profile in profiles.items():
    if not isinstance(profile, dict):
        errors.append(f"profiles.{key}: must be a dict")
        continue

    # 字段完整性
    for field in PROFILE_REQUIRED_FIELDS:
        if field not in profile:
            errors.append(f"profiles.{key}: missing field '{field}'")

    # family == key
    if profile.get("family") != key:
        errors.append(f"profiles.{key}: family '{profile.get('family')}' != key '{key}'")

    # capability_modes 是列表，每项有 capability_id
    for i, mode in enumerate(profile.get("capability_modes", [])):
        if not isinstance(mode, dict):
            errors.append(f"profiles.{key}.capability_modes[{i}]: must be a dict")
            continue
        cap_id = mode.get("capability_id", "")
        if cap_id and cap_id not in all_cap_ids:
            errors.append(f"profiles.{key}.capability_modes[{i}]: capability_id '{cap_id}' not in registry")

    # capability lists
    for list_field in ["verified_capabilities", "direct_testable_capabilities", "guarded_capabilities", "not_default_executable"]:
        for cap_id in profile.get(list_field, []):
            if cap_id not in all_cap_ids:
                errors.append(f"profiles.{key}.{list_field}: capability_id '{cap_id}' not in registry")

    # recommended_workflows 必须在 workflows
    for wf_id in profile.get("recommended_workflows", []):
        if wf_id not in EXPECTED_WORKFLOWS:
            errors.append(f"profiles.{key}.recommended_workflows: workflow '{wf_id}' not in expected workflows")

    # recommended_scenarios 必须在 scenarios
    for sc_id in profile.get("recommended_scenarios", []):
        if sc_id not in EXPECTED_SCENARIOS:
            errors.append(f"profiles.{key}.recommended_scenarios: scenario '{sc_id}' not in expected scenarios")

    # model_notes 结构校验
    for i, note in enumerate(profile.get("model_notes", [])):
        if not isinstance(note, dict):
            errors.append(f"profiles.{key}.model_notes[{i}]: must be a dict")
            continue
        for field in MODEL_NOTES_REQUIRED_FIELDS:
            if field not in note:
                errors.append(f"profiles.{key}.model_notes[{i}]: missing field '{field}'")
        source = note.get("source", "")
        if source and source not in VALID_SOURCES:
            errors.append(f"profiles.{key}.model_notes[{i}]: source '{source}' not in {VALID_SOURCES}")
        rec_level = note.get("recommendation_level", "")
        if rec_level and rec_level not in VALID_RECOMMENDATION_LEVELS:
            errors.append(f"profiles.{key}.model_notes[{i}]: recommendation_level '{rec_level}' not in {VALID_RECOMMENDATION_LEVELS}")
        if not isinstance(note.get("best_for", []), list):
            errors.append(f"profiles.{key}.model_notes[{i}]: 'best_for' must be a list")

profiles_ok = len([p for p in profiles.values() if isinstance(p, dict) and p.get("family") in EXPECTED_PROFILES]) == 6
print(f"- profiles: {len(profiles)} / 6 {'OK' if profiles_ok else 'FAIL'}")

# ── 2. 校验 workflows ─────────────────────────────────────────────────────────
workflows = workflows_data.get("workflows", {})
if "schema_version" not in workflows_data:
    errors.append("workflows: missing 'schema_version'")
if not isinstance(workflows, dict):
    errors.append("workflows: 'workflows' must be a dict")
    workflows = {}

if set(workflows.keys()) != EXPECTED_WORKFLOWS:
    missing = EXPECTED_WORKFLOWS - set(workflows.keys())
    extra = set(workflows.keys()) - EXPECTED_WORKFLOWS
    if missing:
        errors.append(f"workflows: missing: {sorted(missing)}")
    if extra:
        errors.append(f"workflows: unexpected: {sorted(extra)}")

for key, workflow in workflows.items():
    if not isinstance(workflow, dict):
        errors.append(f"workflows.{key}: must be a dict")
        continue

    for field in WORKFLOW_REQUIRED_FIELDS:
        if field not in workflow:
            errors.append(f"workflows.{key}: missing field '{field}'")

    if workflow.get("id") != key:
        errors.append(f"workflows.{key}: id '{workflow.get('id')}' != key '{key}'")

    if workflow.get("family") not in EXPECTED_PROFILES:
        errors.append(f"workflows.{key}: family '{workflow.get('family')}' not in {EXPECTED_PROFILES}")

    steps = workflow.get("steps", [])
    if not steps:
        errors.append(f"workflows.{key}: steps is empty")
    else:
        for step in steps:
            # Only validate capability_id for "capability" type steps (not "parameter" steps
            # which may have compound IDs like "chat-openai / chat-anthropic / chat-responses-create")
            if step.get("type") == "capability":
                cap_id = step.get("capability_id", "")
                if cap_id and cap_id not in all_cap_ids:
                    errors.append(f"workflows.{key}.steps: capability_id '{cap_id}' not in registry")

    risk_policy = workflow.get("risk_policy", {})
    for category in ["allow_direct", "guarded", "blocked"]:
        for cap_id in risk_policy.get(category, []):
            if cap_id not in all_cap_ids:
                errors.append(f"workflows.{key}.risk_policy.{category}: capability_id '{cap_id}' not in registry")

workflows_ok = len([w for w in workflows.values() if isinstance(w, dict) and w.get("id") in EXPECTED_WORKFLOWS]) == 5
print(f"- workflows: {len(workflows)} / 5 {'OK' if workflows_ok else 'FAIL'}")

# ── 3. 校验 scenarios ─────────────────────────────────────────────────────────
scenarios = scenarios_data.get("scenarios", {})
if "schema_version" not in scenarios_data:
    errors.append("scenarios: missing 'schema_version'")
if not isinstance(scenarios, dict):
    errors.append("scenarios: 'scenarios' must be a dict")
    scenarios = {}

if set(scenarios.keys()) != EXPECTED_SCENARIOS:
    missing = EXPECTED_SCENARIOS - set(scenarios.keys())
    extra = set(scenarios.keys()) - EXPECTED_SCENARIOS
    if missing:
        errors.append(f"scenarios: missing: {sorted(missing)}")
    if extra:
        errors.append(f"scenarios: unexpected: {sorted(extra)}")

for key, scenario in scenarios.items():
    if not isinstance(scenario, dict):
        errors.append(f"scenarios.{key}: must be a dict")
        continue

    for field in SCENARIO_REQUIRED_FIELDS:
        if field not in scenario:
            errors.append(f"scenarios.{key}: missing field '{field}'")

    if scenario.get("id") != key:
        errors.append(f"scenarios.{key}: id '{scenario.get('id')}' != key '{key}'")

    if scenario.get("capability_family") not in EXPECTED_PROFILES:
        errors.append(f"scenarios.{key}: capability_family '{scenario.get('capability_family')}' not in {EXPECTED_PROFILES}")

    wf_id = scenario.get("workflow_id", "")
    if wf_id and wf_id not in EXPECTED_WORKFLOWS:
        errors.append(f"scenarios.{key}: workflow_id '{wf_id}' not in expected workflows")

    for cap_id in scenario.get("capabilities", []):
        if cap_id not in all_cap_ids:
            errors.append(f"scenarios.{key}.capabilities: capability_id '{cap_id}' not in registry")

scenarios_ok = len([s for s in scenarios.values() if isinstance(s, dict) and s.get("id") in EXPECTED_SCENARIOS]) == 8
print(f"- scenarios: {len(scenarios)} / 8 {'OK' if scenarios_ok else 'FAIL'}")

# ── 4. 引用一致性校验 ─────────────────────────────────────────────────────────
# capability references
cap_ref_errors = []
for key, profile in profiles.items():
    if not isinstance(profile, dict):
        continue
    for list_field in ["verified_capabilities", "direct_testable_capabilities", "guarded_capabilities", "not_default_executable"]:
        for cap_id in profile.get(list_field, []):
            if cap_id not in all_cap_ids:
                cap_ref_errors.append(f"profiles.{key}.{list_field}: '{cap_id}'")
    for i, mode in enumerate(profile.get("capability_modes", [])):
        cap_id = mode.get("capability_id", "")
        if cap_id and cap_id not in all_cap_ids:
            cap_ref_errors.append(f"profiles.{key}.capability_modes[{i}]: '{cap_id}'")

print(f"- capability references: {'OK' if not cap_ref_errors else 'FAIL'}")
for e in cap_ref_errors:
    errors.append(e)

# workflow references
wf_ref_errors = []
for key, profile in profiles.items():
    if not isinstance(profile, dict):
        continue
    for wf_id in profile.get("recommended_workflows", []):
        if wf_id not in EXPECTED_WORKFLOWS:
            wf_ref_errors.append(f"profiles.{key}.recommended_workflows: '{wf_id}'")
for key, scenario in scenarios.items():
    if not isinstance(scenario, dict):
        continue
    wf_id = scenario.get("workflow_id", "")
    if wf_id and wf_id not in EXPECTED_WORKFLOWS:
        wf_ref_errors.append(f"scenarios.{key}.workflow_id: '{wf_id}'")

print(f"- workflow references: {'OK' if not wf_ref_errors else 'FAIL'}")
for e in wf_ref_errors:
    errors.append(e)

# scenario references
sc_ref_errors = []
for key, profile in profiles.items():
    if not isinstance(profile, dict):
        continue
    for sc_id in profile.get("recommended_scenarios", []):
        if sc_id not in EXPECTED_SCENARIOS:
            sc_ref_errors.append(f"profiles.{key}.recommended_scenarios: '{sc_id}'")

print(f"- scenario references: {'OK' if not sc_ref_errors else 'FAIL'}")
for e in sc_ref_errors:
    errors.append(e)

# ── 5. 输出结果 ───────────────────────────────────────────────────────────────
if errors:
    print(f"\n{len(errors)} ERROR(S):")
    for e in errors:
        print(f"  X {e}")
    sys.exit(1)

print("\nAll checks PASSED")
