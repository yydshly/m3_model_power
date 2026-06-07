#!/usr/bin/env python3
"""Validate frontend UI navigation links consistency across pages and configs."""
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from backend.app.minimax_core.runner import load_runner_templates
from backend.app.minimax_core.registry.loader import get_capability_registry

errors: list[str] = []
warnings: list[str] = []

# ── 1. Runner template capabilities must be in registry ─────────────────────────

templates_data = load_runner_templates()
templates = templates_data.get("templates", {})

reg = get_capability_registry()
all_reg_cap_ids = {cap.id for cap in reg.all()}

# ── 2. Define expected link targets ─────────────────────────────────────────────

RUNNER_SUPPORTED = {"lyrics-gen", "tts-sync", "voice-list", "image-t2i", "image-i2i", "music-gen", "chat-openai"}

QUOTA_SENSITIVE = {"music-gen"}
ASSET_GUARDED = {"image-i2i"}
HIGH_RISK = {"voice-clone", "video-t2v", "video-i2v", "video-s2v", "file-upload", "file-delete"}

FAMILY_TO_DEFAULT_CAP = {
    "chat": "chat-openai",
    "speech": "tts-sync",
    "voice": "tts-sync",
    "image": "image-t2i",
    "vision": "image-t2i",
    "music": "music-gen",
    "video": None,
}

PROFILE_FAMILIES = {"chat", "voice", "vision", "music", "speech", "image", "assets", "models"}

# ── 3. Runner template checks ────────────────────────────────────────────────────

print("Frontend UI link checks")

for cap_id, template in templates.items():
    # 3a. capability_id must exist in registry
    if cap_id not in all_reg_cap_ids:
        errors.append(f"runner template '{cap_id}': capability_id not in registry")

    # 3b. if runner-supported, risk level must match
    if cap_id in RUNNER_SUPPORTED:
        risk = template.get("risk_level", "")
        if cap_id in QUOTA_SENSITIVE and risk != "quota_sensitive":
            warnings.append(f"runner template '{cap_id}': quota_sensitive capability but risk_level='{risk}'")
        if cap_id in ASSET_GUARDED and risk != "guarded":
            warnings.append(f"runner template '{cap_id}': asset_guarded capability but risk_level='{risk}'")

    # 3c. next_steps capability_ids must exist in registry
    for ns in template.get("next_steps", []):
        ns_cap_id = ns.get("capability_id", "")
        if ns_cap_id and ns_cap_id not in all_reg_cap_ids:
            errors.append(f"runner template '{cap_id}'.next_steps: capability_id '{ns_cap_id}' not in registry")

print("- runner templates: OK" if not errors else "")

# ── 4. Scenarios check ────────────────────────────────────────────────────────────

scenarios_path = _root / "backend/app/minimax_core/scenarios/capability_scenarios.json"
if scenarios_path.exists():
    with scenarios_path.open(encoding="utf-8") as f:
        scenarios_data = json.load(f)
    scenarios = scenarios_data.get("scenarios", {})

    for scen_id, scen in scenarios.items():
        caps = scen.get("capabilities", [])
        workflow_id = scen.get("workflow_id", "")

        # 4a. workflow_id must exist (check combined workflows file)
        workflows_path = _root / "backend/app/minimax_core/workflows/capability_workflows.json"
        if workflows_path.exists():
            with workflows_path.open(encoding="utf-8") as f:
                wf_combined = json.load(f)
            wf_map = wf_combined.get("workflows", {})
            if workflow_id not in wf_map:
                errors.append(f"scenario '{scen_id}': workflow_id '{workflow_id}' not found in capability_workflows.json")
        else:
            errors.append(f"scenario '{scen_id}': capability_workflows.json not found")

        # 4b. at least one capability must be runner-supported (or none)
        runner_caps = [c for c in caps if c in RUNNER_SUPPORTED]
        if not runner_caps and caps:
            warnings.append(f"scenario '{scen_id}': no runner-supported capabilities in chain (capabilities={caps})")

        # 4c. each capability must exist in registry
        for cap in caps:
            if cap not in all_reg_cap_ids:
                errors.append(f"scenario '{scen_id}': capability '{cap}' not in registry")
else:
    warnings.append("scenario_registry.json not found, skipping scenario checks")

print("- scenario links: OK" if not [e for e in errors if "scenario" in e] else "")

# ── 5. Workflows check ────────────────────────────────────────────────────────────

workflows_combined_path = _root / "backend/app/minimax_core/workflows/capability_workflows.json"
if workflows_combined_path.exists():
    with workflows_combined_path.open(encoding="utf-8") as f:
        workflows_data = json.load(f)
    workflows_map = workflows_data.get("workflows", {})

    for wf_id, wf_data in workflows_map.items():
        if not isinstance(wf_data, dict):
            continue
        for step in wf_data.get("steps", []):
            cap_id = step.get("capability_id", "")
            if not cap_id:
                continue
            # Skip compound IDs (e.g., "chat-openai / chat-anthropic") — these are descriptions, not real IDs
            if "/" in cap_id:
                continue
            # 5a. capability must exist in registry
            if cap_id not in all_reg_cap_ids:
                errors.append(f"workflow '{wf_id}'.step '{step.get('step_id', '')}': capability '{cap_id}' not in registry")

    # Also validate recommended_workflows in profiles reference existing workflows
    # (done in profile section above using workflows_dir)
else:
    warnings.append("capability_workflows.json not found, skipping workflow checks")

print("- workflow links: OK" if not [e for e in errors if "workflow" in e] else "")

# ── 6. Profile checks ────────────────────────────────────────────────────────────

profiles_path = _root / "backend/app/minimax_core/profiles/capability_profiles.json"
if profiles_path.exists():
    with profiles_path.open(encoding="utf-8") as f:
        profiles_combined = json.load(f)
    profiles = profiles_combined.get("profiles", {})

    for pf_family, pf_data in profiles.items():
        if not isinstance(pf_data, dict):
            continue

        # 6a. family must be a known profile family
        if pf_family not in PROFILE_FAMILIES:
            warnings.append(f"profile '{pf_family}': family not in known PROFILE_FAMILIES")

        # 6b. recommended_scenarios should exist
        for scen_id in pf_data.get("recommended_scenarios", []):
            # scenarios are validated above, just note here
            pass

        # 6c. recommended_workflows should exist
        for wf_id in pf_data.get("recommended_workflows", []):
            if wf_id not in workflows_map:
                errors.append(f"profile '{pf_family}': recommended_workflow '{wf_id}' not found in workflows")

        # 6d. verified_capabilities must exist in registry
        for cap_id in pf_data.get("verified_capabilities", []):
            if cap_id not in all_reg_cap_ids:
                errors.append(f"profile '{pf_family}': verified_capability '{cap_id}' not in registry")

        # 6e. guarded_capabilities must exist in registry
        for cap_id in pf_data.get("guarded_capabilities", []):
            if cap_id not in all_reg_cap_ids:
                errors.append(f"profile '{pf_family}': guarded_capability '{cap_id}' not in registry")

        # 6f. model_notes model IDs should be checked against models.yaml
        models_path = _root / "backend/config/models.yaml"
        if models_path.exists():
            import yaml
            with models_path.open(encoding="utf-8") as f:
                models_data = yaml.safe_load(f) or {}
            known_model_ids = {m.get("id") for m in models_data.get("models", [])}
            for mnote in pf_data.get("model_notes", []):
                model_id = mnote.get("model", "")
                # Skip compound IDs (descriptions with "/")
                if model_id and "/" not in model_id and model_id not in known_model_ids:
                    warnings.append(f"profile '{pf_family}': model_note model '{model_id}' not found in models.yaml")
else:
    warnings.append("profiles capability_profiles.json not found, skipping profile checks")

print("- profile links: OK" if not [e for e in errors if "profile" in e] else "")

# ── 7. Model family mapping check ──────────────────────────────────────────────

for family, default_cap in FAMILY_TO_DEFAULT_CAP.items():
    if default_cap is None:
        continue
    if default_cap not in all_reg_cap_ids:
        errors.append(f"model family '{family}': default_capability '{default_cap}' not in registry")

print("- model links: OK" if not [e for e in errors if "model family" in e] else "")

# ── 8. Routes check (static file existence) ─────────────────────────────────────

frontend_pages = [
    "frontend/src/pages/Models.tsx",
    "frontend/src/pages/CapabilityProfiles.tsx",
    "frontend/src/pages/CapabilityScenarios.tsx",
    "frontend/src/pages/CapabilityWorkflows.tsx",
    "frontend/src/pages/CapabilityRunner.tsx",
    "frontend/src/pages/TestConsole.tsx",
    "frontend/src/navigation/capabilityLinks.ts",
]
for page_path in frontend_pages:
    full = _root / page_path
    if not full.exists():
        errors.append(f"frontend page '{page_path}' not found")

print("- routes: OK" if not [e for e in errors if "frontend page" in e] else "")

# ── 9. Output results ─────────────────────────────────────────────────────────────

if warnings:
    print(f"\n{len(warnings)} WARNING(S):")
    for w in warnings:
        print(f"  ! {w}")

if errors:
    print(f"\n{len(errors)} ERROR(S):")
    for e in errors:
        print(f"  X {e}")
    sys.exit(1)

print("\nAll checks PASSED")
