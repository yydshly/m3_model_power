#!/usr/bin/env python3
"""验证 MiniMax 配置读取正确性：Token Plan Key 优先，API Key 兜底，不暴露真实 Key。"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from backend.app.config import settings

errors: list[str] = []
warnings: list[str] = []

# ── 1. Settings can read backend/.env ──────────────────────────────────────
# Just accessing settings.minimax_effective_api_key is enough to verify loading
try:
    _ = settings.minimax_effective_api_key
    _ = settings.minimax_key_source
    print("- Settings loading: OK")
except Exception as e:
    errors.append(f"Settings loading failed: {e}")

# ── 2. minimax_effective_api_key logic correct ──────────────────────────────
has_token_plan = bool(settings.minimax_token_plan_key)
has_api_key = bool(settings.minimax_api_key)
effective = settings.minimax_effective_api_key
source = settings.minimax_key_source

# When token plan is set, it should be the effective key
if has_token_plan and effective != settings.minimax_token_plan_key:
    errors.append("minimax_effective_api_key should equal minimax_token_plan_key when it is set")
if has_token_plan and source != "MINIMAX_TOKEN_PLAN_KEY":
    errors.append("minimax_key_source should be 'MINIMAX_TOKEN_PLAN_KEY' when it is set")

# When only api_key is set, it should be the effective key
if not has_token_plan and has_api_key and effective != settings.minimax_api_key:
    errors.append("minimax_effective_api_key should equal minimax_api_key when token plan is not set")
if not has_token_plan and has_api_key and source != "MINIMAX_API_KEY":
    errors.append("minimax_key_source should be 'MINIMAX_API_KEY' when only api_key is set")

# When neither is set, source should be empty
if not has_token_plan and not has_api_key and source != "":
    errors.append("minimax_key_source should be '' when neither key is set")
if not has_token_plan and not has_api_key and effective != "":
    errors.append("minimax_effective_api_key should be '' when neither key is set")

print(f"- Token Plan Key configured : {has_token_plan}")
print(f"- API Key configured        : {has_api_key}")
print(f"- Effective key present     : {bool(effective)}")
print(f"- Key source               : {source or '-'}")

# ── 3. MINIMAX_TOKEN_PLAN_KEY takes priority ──────────────────────────────
if has_token_plan and has_api_key:
    if settings.minimax_token_plan_key == settings.minimax_api_key:
        warnings.append("Both keys are set to the same value — verify this is intentional")
    if effective == settings.minimax_api_key:
        errors.append("Token Plan Key is set but effective key still returned API Key — priority logic broken")
    if source != "MINIMAX_TOKEN_PLAN_KEY":
        errors.append("Token Plan Key is set but source is not MINIMAX_TOKEN_PLAN_KEY — priority logic broken")

# ── 4. key_source is empty when nothing configured ────────────────────────
if not effective and source != "":
    errors.append("key_source should be '-' or '' when no key is configured")

# ── 5. No real key in output ───────────────────────────────────────────────
# Verify we never expose the actual key value
key_str = settings.minimax_token_plan_key + settings.minimax_api_key
if key_str:
    # We can't check the properties return values without printing them
    # Just ensure the source itself doesn't contain the key
    if source and any(c.isalnum() for c in source) and len(source) > 30:
        errors.append("key_source appears to contain a real key — it should only contain the env var name")

print("\nCapability Runner Template checks")
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
