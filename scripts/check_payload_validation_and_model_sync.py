"""
Guard: check_payload_validation_and_model_sync.py

Checks:
1. payloadValidation.ts exists
2. validatePayloadForCapability contains tts-sync voice_setting.voice_id
3. InvokePanel.tsx calls validatePayloadForCapability
4. InvokePanel.tsx contains updateJsonBodyField or equivalent model→body sync
5. RiskGate copy no longer says "可以执行"
6. Capability.tsx reuses InvocationHistoryPanel
7. Capability.tsx calls getCapabilityHistory
8. demoPayload chat max_tokens >= 512
"""
import re
import sys
from pathlib import Path

FRONTEND = Path("frontend/src")

def check_payload_validation_ts():
    """1. payloadValidation.ts exists"""
    f = FRONTEND / "domain" / "payloadValidation.ts"
    if not f.exists():
        return False, "payloadValidation.ts does not exist"
    content = f.read_text(encoding="utf-8")
    if "validatePayloadForCapability" not in content:
        return False, "validatePayloadForCapability not found in payloadValidation.ts"
    if "tts-sync" not in content:
        return False, "tts-sync case not found in payloadValidation.ts"
    if "voice_setting.voice_id" not in content:
        return False, "voice_setting.voice_id validation not found"
    return True, "payloadValidation.ts exists and has tts-sync voice_setting.voice_id"


def check_invoke_panel_validation():
    """3. InvokePanel calls validatePayloadForCapability"""
    f = FRONTEND / "components" / "InvokePanel.tsx"
    if not f.exists():
        return False, "InvokePanel.tsx does not exist"
    content = f.read_text(encoding="utf-8")
    if "validatePayloadForCapability" not in content:
        return False, "InvokePanel does not import or use validatePayloadForCapability"
    return True, "InvokePanel calls validatePayloadForCapability"


def check_invoke_panel_model_sync():
    """4. InvokePanel contains model→body.model sync logic"""
    f = FRONTEND / "components" / "InvokePanel.tsx"
    if not f.exists():
        return False, "InvokePanel.tsx does not exist"
    content = f.read_text(encoding="utf-8")
    if "updateJsonBodyField" not in content and "updateJsonBody" not in content:
        # Check if model selection actually updates body model
        # Look for pattern where model select onChange updates body JSON
        has_model_onchange = bool(re.search(r"onChange.*setBody.*model", content, re.DOTALL))
        has_model_sync = "model" in content and "setBody" in content
        if not (has_model_onchange or has_model_sync):
            return False, "InvokePanel does not sync model dropdown to JSON body.model"
    return True, "InvokePanel contains model→body.model sync"


def check_riskgate_copy():
    """5. RiskGate copy no longer says '可以执行'"""
    files = [
        FRONTEND / "components" / "InvokePanel.tsx",
        FRONTEND / "pages" / "Capability.tsx",
        FRONTEND / "pages" / "CapabilityRunner.tsx",
    ]
    bad_files = []
    for f in files:
        if f.exists():
            content = f.read_text(encoding="utf-8")
            if "可以执行" in content:
                bad_files.append(f.name)
    if bad_files:
        return False, f"Files still contain '可以执行': {bad_files}"
    return True, "No '可以执行' copy found in InvokePanel, Capability, CapabilityRunner"


def check_capability_history():
    """6 & 7. Capability.tsx reuses InvocationHistoryPanel and calls getCapabilityHistory"""
    f = FRONTEND / "pages" / "Capability.tsx"
    if not f.exists():
        return False, "Capability.tsx does not exist"
    content = f.read_text(encoding="utf-8")
    issues = []
    if "InvocationHistoryPanel" not in content:
        issues.append("InvocationHistoryPanel not imported or used")
    if "getCapabilityHistory" not in content:
        issues.append("getCapabilityHistory not called")
    if "refreshCapabilityHistory" not in content:
        issues.append("refreshCapabilityHistory not defined")
    if "当前能力最近调用记录" not in content:
        issues.append("history section title not found")
    if issues:
        return False, "; ".join(issues)
    return True, "Capability.tsx reuses InvocationHistoryPanel and calls getCapabilityHistory"


def check_demo_payload_max_tokens():
    """8. demoPayload chat max_tokens >= 512"""
    f = FRONTEND / "domain" / "demoPayload.ts"
    if not f.exists():
        return False, "demoPayload.ts does not exist"
    content = f.read_text(encoding="utf-8")

    # Find chat payloads and check max_tokens values
    # Look for patterns like: 'chat-openai': { ... max_tokens: 256
    issues = []
    for cap_id in ["chat-openai", "chat-anthropic", "chat-responses-create"]:
        # Find the max_tokens value for this capability
        pattern = rf"['\"](?:{cap_id})['\"]:\s*\{{[^}}]*max_tokens:\s*(\d+)"
        matches = re.findall(pattern, content, re.DOTALL)
        for m in matches:
            val = int(m)
            if val < 512:
                issues.append(f"{cap_id} max_tokens={val} < 512")
    if issues:
        return False, "; ".join(issues)
    return True, "chat demo max_tokens >= 512"


def main():
    checks = [
        ("payloadValidation.ts exists + tts-sync voice_id", check_payload_validation_ts),
        ("InvokePanel calls validatePayloadForCapability", check_invoke_panel_validation),
        ("InvokePanel model->body.model sync", check_invoke_panel_model_sync),
        ("RiskGate copy not 'ke yi zhi xing'", check_riskgate_copy),
        ("Capability.tsx history module", check_capability_history),
        ("chat demo max_tokens >= 512", check_demo_payload_max_tokens),
    ]

    all_passed = True
    for name, check_fn in checks:
        ok, msg = check_fn()
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {msg}")
        if not ok:
            all_passed = False

    if all_passed:
        print("\nAll checks PASSED.")
        sys.exit(0)
    else:
        print("\nSome checks FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
