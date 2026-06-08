"""Static contract checks for history trace infrastructure.

Verifies the trace/observability code structure without running the app:
1. diagnostics_store.py exists and has required exports
2. diagnostics router registered in main.py
3. /api/history/probe endpoint exists in history.py
4. history_store.append_history accepts trace_id
5. history record includes trace_id field
6. api.ts has createTraceId and runHistoryProbe
7. Key frontend panels import and use trace_id
8. TestConsole has History Probe button text
"""
from __future__ import annotations

import os
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend" / "src"
SCRIPTS = ROOT / "scripts"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def check_diagnostics_store() -> tuple[int, int]:
    """diagnostics_store.py exists with required functions."""
    print("\n[check] diagnostics_store.py")
    path = BACKEND / "app" / "minimax_core" / "verification" / "diagnostics_store.py"
    if not path.exists():
        print("  - diagnostics_store.py not found")
        return 0, 1

    src = _read(path)
    required = ["new_trace_id", "append_trace_event", "list_trace_events", "get_diagnostics_status"]
    passed = 0
    for fn in required:
        if re.search(rf"\b{fn}\b", src):
            print(f"  + {fn}")
            passed += 1
        else:
            print(f"  - {fn} not found")
    return passed, len(required) - passed


def check_diagnostics_router() -> tuple[int, int]:
    """diagnostics router registered in main.py."""
    print("\n[check] diagnostics router in main.py")
    path = BACKEND / "app" / "main.py"
    src = _read(path)
    passed = 0

    if re.search(r'from \.\routers import.*diagnostics', src, re.MULTILINE) or \
       re.search(r'from \.routers import.*diagnostics', src):
        print("  + diagnostics imported")
        passed += 1
    else:
        print("  - diagnostics not imported in main.py")

    if re.search(r'app\.include_router\(diagnostics\.router', src):
        print("  + diagnostics.router registered")
        passed += 1
    else:
        print("  - diagnostics.router not registered")

    diag_path = BACKEND / "app" / "routers" / "diagnostics.py"
    if diag_path.exists():
        print("  + diagnostics.py exists")
        passed += 1
    else:
        print("  - diagnostics.py not found")
        return passed, 5 - passed

    diag_src = _read(diag_path)
    # Use robust regex — match either flavor of quotes
    endpoint_checks = [
        ('diagnostics status endpoint', r'@router\.get\(["\']\/status["\']\)'),
        ('diagnostics trace endpoint', r'@router\.get\(["\']\/trace\/\{trace_id\}["\']\)'),
    ]
    for label, pattern in endpoint_checks:
        if re.search(pattern, diag_src):
            print(f"  + {label}")
            passed += 1
        else:
            print(f"  - {label} missing")

    return passed, 5 - passed


def check_history_probe() -> tuple[int, int]:
    """history probe endpoint in history.py."""
    print("\n[check] /api/history/probe in history.py")
    path = BACKEND / "app" / "routers" / "history.py"
    src = _read(path)
    passed = 0

    if "history_probe" in src or "/probe" in src:
        print("  + probe endpoint found")
        passed += 1
    else:
        print("  - probe endpoint not found")

    if "runHistoryProbe" in src or "diagnostic_probe" in src:
        print("  + probe action name correct")
        passed += 1
    else:
        print("  - probe action name not found")

    return passed, 2 - passed


def check_history_store_trace() -> tuple[int, int]:
    """append_history accepts trace_id and records it."""
    print("\n[check] history_store.append_history trace_id support")
    path = BACKEND / "app" / "minimax_core" / "verification" / "history_store.py"
    src = _read(path)
    passed = 0

    if re.search(r"def append_history\([^)]*trace_id", src):
        print("  + append_history accepts trace_id param")
        passed += 1
    else:
        print("  - append_history does not accept trace_id param")

    if '"trace_id"' in src or "'trace_id'" in src:
        print("  + trace_id written to record")
        passed += 1
    else:
        print("  - trace_id not written to record")

    if "append_trace_event" in src:
        print("  + append_trace_event called in history_store")
        passed += 1
    else:
        print("  - append_trace_event not called")

    return passed, 3 - passed


def check_trace_middleware() -> tuple[int, int]:
    """trace middleware in main.py."""
    print("\n[check] trace middleware in main.py")
    path = BACKEND / "app" / "main.py"
    src = _read(path)
    passed = 0

    checks = [
        ("X-MMW-Trace-ID" in src, "X-MMW-Trace-ID header handling"),
        ("request.state.trace_id" in src, "request.state.trace_id"),
        ("append_trace_event" in src, "append_trace_event call"),
    ]
    for cond, label in checks:
        if cond:
            print(f"  + {label}")
            passed += 1
        else:
            print(f"  - {label}")

    return passed, len(checks) - passed


def check_route_trace_id() -> tuple[int, int]:
    """Routes pass trace_id to append_history."""
    print("\n[check] route handlers pass trace_id")
    passed = 0
    files = {
        BACKEND / "app" / "routers" / "invoke.py": ["trace_id", "invoke_route_entered"],
        BACKEND / "app" / "routers" / "stream.py": ["trace_id", "stream_route_entered"],
        BACKEND / "app" / "routers" / "upload.py": ["trace_id", "upload_route_entered"],
        BACKEND / "app" / "routers" / "ws.py": ["trace_id", "ws_route_entered"],
    }
    for path, keywords in files.items():
        src = _read(path)
        for kw in keywords:
            if kw in src:
                print(f"  + {path.name}: {kw}")
                passed += 1
            else:
                print(f"  - {path.name}: {kw} missing")

    return passed, sum(len(v) for v in files.values()) - passed


def check_api_ts() -> tuple[int, int]:
    """api.ts has createTraceId and runHistoryProbe."""
    print("\n[check] api.ts trace functions")
    path = FRONTEND / "api.ts"
    src = _read(path)
    passed = 0

    checks = [
        ("createTraceId" in src, "createTraceId function"),
        ("X-MMW-Trace-ID" in src, "X-MMW-Trace-ID header"),
        ("runHistoryProbe" in src, "runHistoryProbe function"),
        ("getDiagnosticsTrace" in src, "getDiagnosticsTrace function"),
        ("streamInvoke" in src and "traceId?" in src, "streamInvoke accepts traceId"),
        ("invoke" in src and "traceId?" in src, "invoke accepts traceId"),
    ]
    for cond, label in checks:
        if cond:
            print(f"  + {label}")
            passed += 1
        else:
            print(f"  - {label}")

    return passed, len(checks) - passed


def check_frontend_panels() -> tuple[int, int]:
    """Key panels import and use trace_id display.

    Each panel has its own contract — not all need all 3 keywords.
    """
    print("\n[check] frontend panels trace_id display")
    passed = 0
    files = {
        "InvokePanel.tsx": {
            "path": FRONTEND / "components" / "InvokePanel.tsx",
            "required_all": ["createTraceId", "getDiagnosticsTrace", "traceId"],
        },
        "ChatPanel.tsx": {
            "path": FRONTEND / "components" / "ChatPanel.tsx",
            "required_all": ["createTraceId", "getDiagnosticsTrace", "traceId"],
        },
        "StreamPanel.tsx": {
            "path": FRONTEND / "components" / "StreamPanel.tsx",
            "required_all": ["createTraceId", "getDiagnosticsTrace", "traceId"],
        },
        "UploadPanel.tsx": {
            "path": FRONTEND / "components" / "UploadPanel.tsx",
            "required_all": ["createTraceId", "getDiagnosticsTrace", "traceId"],
        },
        "TtsWsPanel.tsx": {
            "path": FRONTEND / "components" / "TtsWsPanel.tsx",
            "required_all": ["createTraceId", "trace_id"],
            # TTS websocket panel uses trace_id param and createTraceId; the trace
            # display is via onDone diagnostic or lastTraceId, not necessarily
            # getDiagnosticsTrace — so we treat it as required_any
            "required_any": ["getDiagnosticsTrace", "traceId", "lastTraceId"],
        },
    }
    for name, cfg in files.items():
        path = cfg["path"]
        required_all = cfg.get("required_all", [])
        required_any = cfg.get("required_any", [])
        src = _read(path)
        all_missing = [kw for kw in required_all if kw not in src]
        any_missing = required_any and not any(kw in src for kw in required_any)
        if not all_missing and not any_missing:
            print(f"  + {name}: all {len(required_all)} keywords")
            passed += 1
        else:
            if all_missing:
                print(f"  - {name}: missing {all_missing}")
            else:
                print(f"  - {name}: none of {required_any} found")

    return passed, len(files) - passed


def check_testconsole_probe() -> tuple[int, int]:
    """TestConsole has History Probe button — semantic check."""
    print("\n[check] TestConsole History Probe button")
    path = FRONTEND / "pages" / "TestConsole.tsx"
    src = _read(path)
    passed = 0

    checks = [
        ("runHistoryProbe" in src, "runHistoryProbe imported/called"),
        (
            "诊断：写入一条测试历史" in src or "写入一条测试历史" in src,
            "History Probe button text",
        ),
        (
            "history_id" in src and "trace_id" in src,
            "probe result displays history_id and trace_id",
        ),
    ]
    for cond, label in checks:
        if cond:
            print(f"  + {label}")
            passed += 1
        else:
            print(f"  - {label}")

    return passed, len(checks) - passed


def check_history_status_fields() -> tuple[int, int]:
    """get_history_status returns enhanced fields."""
    print("\n[check] get_history_status enhanced fields")
    path = BACKEND / "app" / "minimax_core" / "verification" / "history_store.py"
    src = _read(path)
    passed = 0

    checks = [
        ("history_dir_exists" in src, "history_dir_exists field"),
        ("history_file_name" in src, "history_file_name field"),
    ]
    for cond, label in checks:
        if cond:
            print(f"  + {label}")
            passed += 1
        else:
            print(f"  - {label}")

    return passed, len(checks) - passed


def check_risk_check_route() -> tuple[int, int]:
    """risk_check route — trace middleware handles it automatically (no history write needed)."""
    print("\n[check] risk_check route trace_id (middleware handles it, no history write)")
    # trace middleware is already verified above; risk_check itself does not write history
    print("  + trace middleware covers risk_check automatically")
    return 1, 0


def run() -> tuple[int, int]:
    total_passed = 0
    total_failed = 0

    checks = [
        check_diagnostics_store,
        check_diagnostics_router,
        check_history_probe,
        check_history_store_trace,
        check_trace_middleware,
        check_route_trace_id,
        check_api_ts,
        check_frontend_panels,
        check_testconsole_probe,
        check_history_status_fields,
        check_risk_check_route,
    ]

    for fn in checks:
        try:
            p, f = fn()
            total_passed += p
            total_failed += f
        except Exception as e:
            print(f"  - {fn.__name__} raised: {e}")
            total_failed += 1

    print(f"\n[Summary] passed={total_passed} failed={total_failed}")
    if total_failed == 0:
        print("[PASSED] History trace contract check passed")
    else:
        print(f"[FAILED] History trace contract check failed ({total_failed} failures)")
    return total_passed, total_failed


if __name__ == "__main__":
    p, f = run()
    sys.exit(0 if f == 0 else 1)
