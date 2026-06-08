#!/usr/bin/env python3
"""Core dev script for m3_model_power.

Implements: doctor, install, dev, backend, frontend, check, build, clean, stop
"""
from __future__ import annotations

import os
import json
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
STARTUP_LOCK = ROOT / "backend" / "runtime" / "dev_startup.lock"
IS_WINDOWS = os.name == "nt"

# ── helpers ──────────────────────────────────────────────────────────────────


def find_process_on_port(port: int) -> list[dict]:
    """Return list of dicts with pid/process info for processes on port."""
    results = []
    seen_pids = set()
    try:
        output = subprocess.check_output(
            ["netstat", "-ano"], text=True, encoding="utf-8", errors="replace"
        )
        for line in output.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid in seen_pids:
                        continue
                    seen_pids.add(pid)
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


def check_url_status(url: str, timeout: int = 5) -> bool:
    """Return True if URL returns HTTP 200 within timeout."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def check_url_contains(url: str, needle: str, timeout: int = 5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            if r.status != 200:
                return False
            body = r.read(100_000).decode("utf-8", errors="replace")
            return needle in body
    except Exception:
        return False


def wait_for_health(url: str, timeout: int = 30) -> bool:
    """Wait for URL to return 200 within timeout seconds."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_url_status(url, timeout=3):
            return True
        time.sleep(1)
    return False


def wait_for_port_free(port: int, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not find_process_on_port(port):
            return True
        time.sleep(0.3)
    return not find_process_on_port(port)


def pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if IS_WINDOWS:
            return get_process_detail(pid) is not None
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def acquire_startup_lock(timeout: float = 45.0) -> int:
    STARTUP_LOCK.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(str(STARTUP_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            return fd
        except FileExistsError:
            try:
                owner_text = STARTUP_LOCK.read_text(encoding="utf-8").strip()
                owner_pid = int(owner_text) if owner_text else 0
            except Exception:
                owner_pid = 0
            if not pid_is_running(owner_pid):
                try:
                    STARTUP_LOCK.unlink()
                    continue
                except OSError:
                    pass
            if time.time() >= deadline:
                print("[FAIL] Another launcher is still starting the project.")
                print(f"       Lock file: {STARTUP_LOCK}")
                print("       Wait a moment, or run 'python start.py stop' to inspect ports.")
                sys.exit(1)
            print("[INFO] Another launcher is starting; waiting for it to finish...")
            time.sleep(1)


def release_startup_lock(fd: int | None) -> None:
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        STARTUP_LOCK.unlink()
    except OSError:
        pass


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
            [shutil.which("node") or "node", "--version"],
            text=True, encoding="utf-8", errors="replace",
        ).strip()
        checks.append((f"Node: {node_out}", True, None))
    except Exception:
        checks.append(("Node: not found", False, None))

    # 4. npm
    try:
        npm_out = subprocess.check_output(
            [shutil.which("npm") or "npm", "--version"],
            text=True, encoding="utf-8", errors="replace",
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
        # Try to detect if it's our healthy backend
        healthy = check_url_status(f"http://127.0.0.1:{BACKEND_PORT}/api/health", timeout=3)
        pid_info = f"PID={p1[0]['pid']}"
        if healthy:
            checks.append(
                (f"Port {BACKEND_PORT} occupied (healthy backend)", True,
                 f"Backend already running on port {BACKEND_PORT}; dev will reuse it.")
            )
        else:
            checks.append(
                (f"Port {BACKEND_PORT} occupied (unknown process)", False,
                 f"Port {BACKEND_PORT} occupied by unknown process. "
                 f"Run 'python start.py stop' for details.")
            )
    else:
        checks.append((f"Port {BACKEND_PORT} free", True, None))

    # 7. Port 5175
    p2 = find_process_on_port(FRONTEND_PORT)
    if p2:
        reachable = check_url_status(f"http://127.0.0.1:{FRONTEND_PORT}", timeout=3)
        if reachable:
            checks.append(
                (f"Port {FRONTEND_PORT} serves frontend", True,
                 f"Frontend already running on port {FRONTEND_PORT}; dev will reuse it.")
            )
        else:
            checks.append(
                (f"Port {FRONTEND_PORT} occupied (unknown process)", False,
                 f"Port {FRONTEND_PORT} occupied by unknown process. "
                 f"Run 'python start.py stop' for details.")
            )
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
        print(f"       Stop it first or run 'python start.py stop --kill'.")
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
        print(f"       Stop it first or run 'python start.py stop --kill'.")
        return
    print(f"Starting frontend on http://localhost:{FRONTEND_PORT} ...")
    run_or_fail(
        [shutil.which("npm") or "npm", "run", "dev", "--",
         "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
    )


DEV_BANNER = """\
m3_model_power development launcher

Default action:
  start backend on http://127.0.0.1:8777
  start frontend on http://localhost:5175

Useful commands:
  python start.py doctor    check local environment
  python start.py install  install backend/frontend dependencies
  python start.py check    run quick checks
  python start.py backend   start backend only
  python start.py frontend start frontend only
  python start.py stop     inspect occupied ports only
  python start.py stop --kill inspect and stop occupied port processes
"""


def cmd_dev() -> None:
    print(DEV_BANNER)
    startup_lock_fd = acquire_startup_lock()

    be_proc = None
    fe_proc = None
    be_reused = False
    fe_reused = False

    # ── Backend ────────────────────────────────────────────────────────────
    if port_in_use(BACKEND_PORT):
        healthy = check_url_status(f"http://127.0.0.1:{BACKEND_PORT}/api/health", timeout=5)
        if healthy:
            print(f"[INFO] Backend already running on http://127.0.0.1:{BACKEND_PORT} — reusing it.")
            be_reused = True
        else:
            procs = find_process_on_port(BACKEND_PORT)
            pid_info = ", ".join(f"{p['name']} (PID {p['pid']})" for p in procs)
            print(f"[FAIL] Port {BACKEND_PORT} is occupied by unknown process ({pid_info}).")
            print(f"       Cannot start backend. Free port {BACKEND_PORT} first.")
            print()
            print("Quick排查:")
            print(f"  netstat -ano | findstr :{BACKEND_PORT}")
            if procs:
                root_pid = find_project_process_root(int(procs[0]["pid"]))
                print(f"  tasklist /FI \"PID eq {procs[0]['pid']}\"")
                print(f"  taskkill /PID {root_pid} /T /F")
            else:
                print("  python start.py stop")
            print()
            print("Stopping frontend if it was started by this launcher...")
            release_startup_lock(startup_lock_fd)
            sys.exit(1)
    else:
        be_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--reload", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
            cwd=BACKEND_DIR,
        )
        print(f"[INFO] Backend starting, PID={be_proc.pid}")
        print(f"[INFO] Waiting for backend health...")
        if wait_for_health(f"http://127.0.0.1:{BACKEND_PORT}/api/health"):
            print(f"[PASS] Backend is up on http://127.0.0.1:{BACKEND_PORT}")
        else:
            print(f"[WARN] Backend health check timed out — continuing anyway")

    # ── Frontend ───────────────────────────────────────────────────────────
    if port_in_use(FRONTEND_PORT):
        reachable = check_url_contains(
            f"http://127.0.0.1:{FRONTEND_PORT}",
            "/src/main.tsx",
            timeout=5,
        )
        if reachable:
            print(f"[INFO] Frontend already running on http://localhost:{FRONTEND_PORT} — reusing it.")
            fe_reused = True
        else:
            procs = find_process_on_port(FRONTEND_PORT)
            pid_info = ", ".join(f"{p['name']} (PID {p['pid']})" for p in procs)
            print(f"[FAIL] Port {FRONTEND_PORT} is occupied by unknown process ({pid_info}).")
            print(f"       Cannot start frontend. Free port {FRONTEND_PORT} first.")
            print()
            print("Quick排查:")
            print(f"  netstat -ano | findstr :{FRONTEND_PORT}")
            if procs:
                root_pid = find_project_process_root(int(procs[0]["pid"]))
                print(f"  tasklist /FI \"PID eq {procs[0]['pid']}\"")
                print(f"  taskkill /PID {root_pid} /T /F")
            else:
                print("  python start.py stop")
            print()
            print("Stopping backend...")
            if be_proc:
                kill_process_tree(be_proc.pid, "backend")
                be_proc.wait()
            release_startup_lock(startup_lock_fd)
            sys.exit(1)
    else:
        fe_proc = subprocess.Popen(
            [shutil.which("npm") or "npm", "run", "dev", "--",
             "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
            cwd=FRONTEND_DIR,
        )
        print(f"[INFO] Frontend starting, PID={fe_proc.pid}")

    # ── Summary ─────────────────────────────────────────────────────────────
    print()
    print("=" * 50)
    print("Workbench is ready.")
    print()
    print("Backend:")
    print(f"  http://127.0.0.1:{BACKEND_PORT}/api/health")
    print()
    print("Frontend:")
    print(f"  http://localhost:{FRONTEND_PORT}")
    print()
    print("Pages:")
    print(f"  Overview:          http://localhost:{FRONTEND_PORT}/")
    print(f"  Project Overview:  http://localhost:{FRONTEND_PORT}/project-overview")
    print(f"  Test Console:      http://localhost:{FRONTEND_PORT}/test-console")
    print(f"  Capability Runner: http://localhost:{FRONTEND_PORT}/capability-runner")
    print(f"  Models:            http://localhost:{FRONTEND_PORT}/models-all")
    print("=" * 50)
    print()
    reused_note = ""
    if be_reused or fe_reused:
        reused_note = (
            "Note: Ctrl+C stops processes started by this launcher only. "
            "Processes reused from a previous launch are NOT terminated."
        )
        print(reused_note)
        print()
    release_startup_lock(startup_lock_fd)
    print("Press Ctrl+C to stop processes started by this launcher.")

    try:
        while True:
            if fe_proc and fe_proc.poll() is not None:
                if be_proc and not be_reused and be_proc.poll() is None:
                    print("[INFO] Frontend exited; stopping backend started by this launcher...")
                    kill_process_tree(be_proc.pid, "backend")
                    be_proc.wait()
                break
            if be_proc and not be_reused and be_proc.poll() is not None:
                if fe_proc and not fe_reused and fe_proc.poll() is None:
                    print("[INFO] Backend exited; stopping frontend started by this launcher...")
                    kill_process_tree(fe_proc.pid, "frontend")
                    fe_proc.wait()
                break
            if not fe_proc and be_proc:
                be_proc.wait()
                break
            if not fe_proc and not be_proc:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping processes started by this launcher...")
        if be_proc and not be_reused:
            kill_process_tree(be_proc.pid, "backend")
        if fe_proc and not fe_reused:
            kill_process_tree(fe_proc.pid, "frontend")
        if be_proc and not be_reused:
            be_proc.wait()
        if fe_proc and not fe_reused:
            fe_proc.wait()
        print("[INFO] Done.")


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


def get_process_detail(pid: int) -> dict | None:
    """Get process details via PowerShell Get-CimInstance."""
    if not IS_WINDOWS:
        return None
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" | "
                "Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
                "ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except Exception:
                return {"raw": result.stdout}
    except Exception:
        pass
    return None


def project_process_match(detail: dict | None) -> bool:
    if not detail or "raw" in detail:
        return False
    command_line = str(detail.get("CommandLine") or "").lower()
    name = str(detail.get("Name") or "").lower()
    root = str(ROOT).lower()
    if root not in command_line:
        return False
    process_markers = (
        "python" in name,
        "node" in name,
        "npm" in name,
        "cmd" in name,
        "powershell" in name,
        "uvicorn" in command_line,
        "vite" in command_line,
        "app.main:app" in command_line,
        "npm run dev" in command_line,
    )
    return any(process_markers)


def find_project_process_root(pid: int) -> int:
    """Walk upward from a port PID and return the highest related project process."""
    current_pid = pid
    best_pid: int | None = None
    seen: set[int] = set()
    for _ in range(10):
        if current_pid in seen or current_pid <= 0:
            break
        seen.add(current_pid)
        detail = get_process_detail(current_pid)
        if not detail or "raw" in detail:
            break
        if project_process_match(detail):
            best_pid = current_pid
        try:
            current_pid = int(detail.get("ParentProcessId") or 0)
        except Exception:
            break
    return best_pid or pid


def kill_process_tree(pid: int | str, label: str = "process") -> None:
    pid_str = str(pid)
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/PID", pid_str, "/T", "/F"], check=False)
        return
    try:
        os.kill(int(pid_str), 15)
    except Exception:
        pass


def stop_port_process(port: int, pid: int | str) -> bool:
    original_pid = int(pid)
    if IS_WINDOWS and not pid_is_running(original_pid):
        print(f"    [WARN] Port {port} is owned by PID {original_pid}, but that PID is not in the process table.")
        print("    [INFO] This is not a killable process anymore; Windows is still reporting the socket.")
        print("    [HINT] Wait a moment and recheck. If LISTENING remains, restart Windows or the networking stack.")
        return False
    root_pid = find_project_process_root(original_pid)
    if root_pid != original_pid:
        print(f"    [INFO] Port PID {original_pid} belongs to project parent PID {root_pid}")
    print(f"    [WARN] About to kill process tree on port {port}: PID={root_pid}")
    kill_process_tree(root_pid, f"port {port}")
    if wait_for_port_free(port):
        print(f"    [PASS] Port {port} released")
        return True
    remaining = find_process_on_port(port)
    if remaining:
        pid_after = int(remaining[0]["pid"])
        print(f"    [WARN] Port {port} still occupied after kill. PID={pid_after}")
        if IS_WINDOWS and not pid_is_running(pid_after):
            print("    [INFO] The remaining PID is not in the process table, so taskkill cannot remove it.")
            print("    [HINT] Wait a moment and recheck. If LISTENING remains, restart Windows or the networking stack.")
            return False
        detail = get_process_detail(pid_after)
        if detail:
            print("    Process detail:")
            if "raw" in detail:
                for line in detail["raw"].splitlines():
                    print(f"      {line}")
            else:
                print(f"      PID: {detail.get('ProcessId', '?')}")
                print(f"      Name: {detail.get('Name', '?')}")
                print(f"      Parent PID: {detail.get('ParentProcessId', '?')}")
                cmdline = detail.get("CommandLine") or "(not available)"
                print(f"      CommandLine: {cmdline}")
        retry_root = find_project_process_root(pid_after)
        print(f"    [HINT] Try: taskkill /PID {retry_root} /T /F")
    return False


def cmd_stop() -> None:
    do_kill = "--kill" in sys.argv

    print("Port occupancy:")
    for port in [BACKEND_PORT, FRONTEND_PORT]:
        procs = find_process_on_port(port)
        if procs:
            print(f"\n  Port {port}:")
            for p in procs:
                print(f"    PID {p['pid']} ({p['name']})")
                if do_kill:
                    stop_port_process(port, p["pid"])
                else:
                    pid = int(p["pid"])
                    if IS_WINDOWS and not pid_is_running(pid):
                        print("    PID is not in the process table; taskkill cannot remove it.")
                        print("    Recheck after a moment. If LISTENING remains, restart Windows or the networking stack.")
                    else:
                        root_pid = find_project_process_root(pid)
                        if root_pid != pid:
                            print(f"    Project parent PID: {root_pid}")
                        print(f"    Manual kill: taskkill /PID {root_pid} /T /F")
        else:
            print(f"\n  Port {port}: free")

    if not do_kill:
        print("\nInspect only: no processes were stopped.")
        print("Run 'python start.py stop --kill' to inspect and stop occupied port processes.")


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
