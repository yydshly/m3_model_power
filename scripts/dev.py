#!/usr/bin/env python3
"""Core dev script for m3_model_power.

Implements: doctor, install, dev, backend, frontend, check, build, clean, stop
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
BACKEND_PORT = 8777
FRONTEND_PORT = 5175

# ── helpers ──────────────────────────────────────────────────────────────────


def find_process_on_port(port: int) -> list[dict]:
    """Return list of dicts with pid/process info for processes on port."""
    results = []
    try:
        output = subprocess.check_output(
            ["netstat", "-ano"], text=True, encoding="utf-8", errors="replace"
        )
        for line in output.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        p = subprocess.check_output(
                            ["tasklist", "/FI", f"PID eq {pid}"],
                            text=True, encoding="utf-8", errors="replace",
                        )
                        name = p.splitlines()[1].split()[0] if len(p.splitlines()) > 1 else "?"
                    except Exception:
                        name = "?"
                    results.append({"pid": pid, "name": name})
    except Exception:
        pass
    return results


def port_in_use(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return False
    except OSError:
        return True


def wait_for_health(url: str, timeout: int = 30) -> bool:
    """Wait for URL to return 200 within timeout seconds."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def run_or_fail(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command; exit with error message if it fails."""
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"[FAIL] Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)


# ── commands ─────────────────────────────────────────────────────────────────


def cmd_doctor() -> None:
    print("=" * 50)
    print("Environment Doctor")
    print("=" * 50)

    checks = []

    # 1. Project root
    root_ok = (ROOT / "backend" / "pyproject.toml").exists() and (
        ROOT / "frontend" / "package.json"
    ).exists()
    checks.append(("Project root structure", root_ok, None))

    # 2. Python
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append((f"Python: {py_version}", True, None))

    # 3. Node
    try:
        node_out = subprocess.check_output(
            [shutil.which("node") or "node", "--version"], text=True, encoding="utf-8", errors="replace"
        ).strip()
        checks.append((f"Node: {node_out}", True, None))
    except Exception:
        checks.append(("Node: not found", False, None))

    # 4. npm
    try:
        npm_out = subprocess.check_output(
            [shutil.which("npm") or "npm", "--version"], text=True, encoding="utf-8", errors="replace"
        ).strip()
        checks.append((f"npm: {npm_out}", True, None))
    except Exception:
        checks.append(("npm: not found", False, None))

    # 5. app.main import
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        import app.main
        checks.append(("app.main imports OK", True, None))
    except Exception:
        checks.append(("app.main import failed", False, None))

    # 6. Port 8777
    p1 = find_process_on_port(BACKEND_PORT)
    if p1:
        msg = f"Port {BACKEND_PORT} occupied by PID={p1[0]['pid']} ({p1[0]['name']})"
        checks.append((f"Port {BACKEND_PORT} occupied", False, msg))
    else:
        checks.append((f"Port {BACKEND_PORT} free", True, None))

    # 7. Port 5175
    p2 = find_process_on_port(FRONTEND_PORT)
    if p2:
        msg = f"Port {FRONTEND_PORT} occupied by PID={p2[0]['pid']} ({p2[0]['name']})"
        checks.append((f"Port {FRONTEND_PORT} occupied", False, msg))
    else:
        checks.append((f"Port {FRONTEND_PORT} free", True, None))

    # 8. node_modules
    nm = FRONTEND_DIR / "node_modules"
    checks.append((f"frontend/node_modules {'found' if nm.exists() else 'NOT found'}",
                   nm.exists(),
                   "Run: python start.py install" if not nm.exists() else None))

    print()
    for label, ok, hint in checks:
        tag = "PASS" if ok else ("WARN" if hint else "FAIL")
        sym = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[tag]
        print(f"{sym} {label}")
        if hint:
            safe_hint = hint.encode("ascii", errors="replace").decode("ascii")
            print(f"      {safe_hint}")
    print()


def cmd_install() -> None:
    print("Installing dependencies...")
    run_or_fail([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run_or_fail([sys.executable, "-m", "pip", "install", "-e", str(BACKEND_DIR)])
    npm = shutil.which("npm") or "npm"
    run_or_fail([npm, "ci"], cwd=FRONTEND_DIR)
    print("Install complete.")


def cmd_backend() -> None:
    if port_in_use(BACKEND_PORT):
        procs = find_process_on_port(BACKEND_PORT)
        pid_info = ", ".join(f"{p['name']} (PID {p['pid']})" for p in procs)
        print(f"[WARN] Port {BACKEND_PORT} is already in use by: {pid_info}")
        print(f"       Stop it first or kill manually, then run this command again.")
        return
    print(f"Starting backend on http://127.0.0.1:{BACKEND_PORT} ...")
    run_or_fail(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload",
         "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BACKEND_DIR,
    )


def cmd_frontend() -> None:
    if port_in_use(FRONTEND_PORT):
        procs = find_process_on_port(FRONTEND_PORT)
        pid_info = ", ".join(f"{p['name']} (PID {p['pid']})" for p in procs)
        print(f"[WARN] Port {FRONTEND_PORT} is already in use by: {pid_info}")
        print(f"       Stop it first or kill manually, then run this command again.")
        return
    print(f"Starting frontend on http://localhost:{FRONTEND_PORT} ...")
    run_or_fail(
        [shutil.which("npm") or "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
    )


def cmd_dev() -> None:
    print("=" * 50)
    print("Dev mode — starting backend + frontend")
    print("=" * 50)

    # Check ports
    be_busy = port_in_use(BACKEND_PORT)
    fe_busy = port_in_use(FRONTEND_PORT)

    if be_busy:
        print(f"[WARN] Backend port {BACKEND_PORT} is occupied — backend may not start")
    if fe_busy:
        print(f"[WARN] Frontend port {FRONTEND_PORT} is occupied — frontend may not start")

    # Start backend
    be_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--reload", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"[INFO] Backend PID={be_proc.pid}")

    print(f"[INFO] Waiting for backend health at http://127.0.0.1:{BACKEND_PORT}/api/health ...")
    if wait_for_health(f"http://127.0.0.1:{BACKEND_PORT}/api/health"):
        print("[PASS] Backend is up")
    else:
        print("[WARN] Backend health check timed out — continuing anyway")

    # Start frontend
    fe_proc = subprocess.Popen(
        [shutil.which("npm") or "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"[INFO] Frontend PID={fe_proc.pid}")

    print()
    print("=" * 50)
    print("Backend:  http://127.0.0.1:8777")
    print("Frontend: http://localhost:5175")
    print()
    print("Pages:")
    print("  /                         总览")
    print("  /project-overview         项目说明")
    print("  /test-console             高级测试")
    print("  /capability-runner        能力体验")
    print("  /models-all               模型列表")
    print("=" * 50)
    print()
    print("Press Ctrl+C to stop both processes.")

    try:
        be_proc.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Stopping...")
        fe_proc.terminate()
        be_proc.terminate()
        fe_proc.wait()
        be_proc.wait()
        print("[INFO] Stopped.")


def cmd_check() -> None:
    print("Running quick checks...")
    guards = [
        "scripts/check_runtime_smoke.py",
        "scripts/check_project_overview_page.py",
        "scripts/check_github_actions_ci_yaml.py",
        "scripts/check_history_result_summary.py",
    ]
    all_ok = True
    for g in guards:
        print(f"\n[CHECK] {g}")
        r = subprocess.run([sys.executable, g], cwd=ROOT)
        if r.returncode != 0:
            all_ok = False
    print()
    subprocess.run(
        [sys.executable, "-m", "compileall", "backend", "scripts"],
        cwd=ROOT,
    )
    print()
    npm = shutil.which("npm") or "npm"
    r = subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR)
    if r.returncode != 0:
        all_ok = False
    if all_ok:
        print("\n[PASS] All checks passed")
    else:
        print("\n[FAIL] Some checks failed")
        sys.exit(1)


def cmd_build() -> None:
    print("Building...")
    subprocess.run(
        [sys.executable, "-m", "compileall", "backend", "scripts"],
        cwd=ROOT,
    )
    npm = shutil.which("npm") or "npm"
    r = subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR)
    if r.returncode != 0:
        sys.exit(1)
    print("Build complete.")


def cmd_clean() -> None:
    print("Cleaning runtime artifacts...")
    files_to_remove = [
        ROOT / "backend" / "runtime" / "test_console" / "history.jsonl",
        ROOT / "backend" / "runtime" / "diagnostics" / "trace.jsonl",
        FRONTEND_DIR / "node_modules" / ".vite",
    ]
    for f in files_to_remove:
        if f.exists():
            if f.is_dir():
                shutil.rmtree(f)
                print(f"[CLEAN] Removed directory: {f}")
            else:
                f.unlink()
                print(f"[CLEAN] Removed file: {f}")
        else:
            print(f"[SKIP] Not found: {f}")
    print("Clean complete.")


def cmd_stop() -> None:
    print("Port occupancy:")
    for port in [BACKEND_PORT, FRONTEND_PORT]:
        procs = find_process_on_port(port)
        if procs:
            print(f"\n  Port {port}:")
            for p in procs:
                print(f"    PID {p['pid']} ({p['name']})")
                print(f"    Manual kill: taskkill //PID {p['pid']} //F")
        else:
            print(f"\n  Port {port}: free")


# ── main ─────────────────────────────────────────────────────────────────────


COMMANDS = {
    "doctor": cmd_doctor,
    "install": cmd_install,
    "dev": cmd_dev,
    "backend": cmd_backend,
    "frontend": cmd_frontend,
    "check": cmd_check,
    "build": cmd_build,
    "clean": cmd_clean,
    "stop": cmd_stop,
}


def main() -> None:
    if not sys.argv[1:]:
        cmd_dev()
        return

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)

    COMMANDS[cmd]()


if __name__ == "__main__":
    main()
