from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

import uvicorn

HOST = "127.0.0.1"
PREFERRED_PORT = 8000
MAX_PORT_SCAN = 120
STATE_DIR = Path.home() / ".tracktech_metainfo_updater"
PID_FILE = STATE_DIR / "app.pid"
PORT_FILE = STATE_DIR / "app.port"
BIN_DIR = STATE_DIR / "bin"
LAUNCHER_LOG_FILE = STATE_DIR / "launcher.log"
APP_TITLE = "TrackTECH Meta Updater"


def _log(message: str) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        with LAUNCHER_LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{timestamp}Z | {message}\n")
    except OSError:
        pass


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _run_osascript(script: str) -> str | None:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        _log(f"osascript invocation failed: {exc}")
        return None

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        _log(f"osascript returned {result.returncode}: {stderr}")
        return None
    return result.stdout.strip()


def _show_dialog(message: str) -> None:
    title = _escape_applescript(APP_TITLE)
    body = _escape_applescript(message)
    dialog_result = _run_osascript(
        f'display dialog "{body}" with title "{title}" buttons {{"OK"}} default button "OK"'
    )
    if dialog_result is None:
        _log(f"Dialog fallback (no UI): {message}")


def _ask_yes_no(message: str, yes_label: str = "Yes", no_label: str = "No") -> bool:
    title = _escape_applescript(APP_TITLE)
    body = _escape_applescript(message)
    yes = _escape_applescript(yes_label)
    no = _escape_applescript(no_label)
    result = _run_osascript(
        (
            f'display dialog "{body}" with title "{title}" '
            f'buttons {{"{no}", "{yes}"}} default button "{yes}"'
        )
    )
    return bool(result and f"button returned:{yes_label}" in result)


def _choose_action() -> str:
    title = _escape_applescript(APP_TITLE)
    result = _run_osascript(
        (
            'choose from list {"Start", "Stop"} '
            f'with title "{title}" '
            'with prompt "Choose what to do:" '
            'default items {"Start"} '
            'OK button name "Continue" '
            'cancel button name "Cancel"'
        )
    )
    if result == "false":
        return "cancel"
    if not result:
        return "error"
    if "Start" in result:
        return "start"
    if "Stop" in result:
        return "stop"
    return "error"


def _resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def _health_url(port: int) -> str:
    return f"http://{HOST}:{port}/health"


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((HOST, port)) == 0


def _health_ok(port: int, timeout: float = 0.6) -> bool:
    try:
        with urllib.request.urlopen(_health_url(port), timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def _read_int_file(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _cleanup_state() -> None:
    for path in [PID_FILE, PORT_FILE]:
        try:
            path.unlink()
        except OSError:
            pass


def _terminate_pid(pid: int) -> None:
    if not _is_pid_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return

    for _ in range(20):
        if not _is_pid_alive(pid):
            return
        time.sleep(0.2)

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _find_free_port(start_port: int) -> int:
    for port in range(start_port, start_port + MAX_PORT_SCAN):
        if not _is_port_in_use(port):
            return port
    raise RuntimeError("Could not find a free local port.")


def _resolve_command(command: str, extra_candidates: list[Path]) -> Path | None:
    on_path = shutil.which(command)
    if on_path:
        return Path(on_path)

    for candidate in extra_candidates:
        if candidate.exists():
            return candidate
    return None


def _clear_quarantine(path: Path) -> None:
    xattr_path = shutil.which("xattr")
    if not xattr_path:
        return

    subprocess.run(
        [xattr_path, "-d", "com.apple.quarantine", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _can_run_exiftool(path: Path) -> bool:
    try:
        result = subprocess.run(
            [str(path), "-ver"],
            capture_output=True,
            text=True,
            check=False,
            timeout=12,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return result.returncode == 0


def _ensure_executable(path: Path) -> bool:
    if not path.exists():
        return False

    if os.access(path, os.X_OK):
        return True

    try:
        mode = path.stat().st_mode
        path.chmod(mode | 0o111)
    except OSError:
        return False

    return os.access(path, os.X_OK)


def _stage_bundled_exiftool(source: Path) -> Path:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    staged = BIN_DIR / "exiftool"
    shutil.copy2(source, staged)
    staged.chmod(0o755)
    _clear_quarantine(staged)
    return staged


def _resolve_exiftool_from_candidates(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if not candidate.exists():
            continue
        if not _ensure_executable(candidate):
            continue

        _clear_quarantine(candidate)
        if _can_run_exiftool(candidate):
            return candidate

        _log(f"ExifTool candidate failed self-test: {candidate}")
    return None


def _ensure_exiftool_available(root: Path) -> None:
    _log(f"Resolving ExifTool from root: {root}")

    env_path = os.environ.get("EXIFTOOL_PATH")
    if env_path:
        resolved_env = _resolve_exiftool_from_candidates([Path(env_path)])
        if resolved_env:
            os.environ["EXIFTOOL_PATH"] = str(resolved_env)
            return
        _log(f"Configured EXIFTOOL_PATH is not runnable: {env_path}")

    bundled_candidates = [
        root / "bin" / "exiftool",
        root / "bin" / "exiftool.exe",
    ]
    bundled = _resolve_exiftool_from_candidates(bundled_candidates)
    if bundled:
        os.environ["EXIFTOOL_PATH"] = str(bundled)
        return

    # DMG-mounted app bundles may expose bundled exiftool without exec permission.
    for candidate in bundled_candidates:
        if not candidate.exists():
            continue
        try:
            staged = _stage_bundled_exiftool(candidate)
        except OSError:
            _log(f"Failed to stage bundled ExifTool: {candidate}")
            continue
        if _can_run_exiftool(staged):
            os.environ["EXIFTOOL_PATH"] = str(staged)
            return
        _log(f"Staged bundled ExifTool failed self-test: {staged}")

    installed_candidates: list[Path] = []
    on_path = shutil.which("exiftool")
    if on_path:
        installed_candidates.append(Path(on_path))
    installed_candidates.extend(
        [
            Path("/opt/homebrew/bin/exiftool"),
            Path("/usr/local/bin/exiftool"),
            Path("/usr/bin/exiftool"),
        ]
    )

    installed = _resolve_exiftool_from_candidates(installed_candidates)
    if installed:
        os.environ["EXIFTOOL_PATH"] = str(installed)
        return

    wants_install = _ask_yes_no(
        "ExifTool is required but was not found. Install now using Homebrew?",
        yes_label="Install",
        no_label="Cancel",
    )
    if not wants_install:
        raise RuntimeError("ExifTool is required. Install it with: brew install exiftool")

    brew_path = _resolve_command(
        "brew",
        [
            Path("/opt/homebrew/bin/brew"),
            Path("/usr/local/bin/brew"),
        ],
    )
    if not brew_path:
        raise RuntimeError(
            "Homebrew was not found. Install Homebrew first, then run: brew install exiftool"
        )

    result = subprocess.run(
        [str(brew_path), "install", "exiftool"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "Unknown installer error").strip()
        tail = "\n".join(output.splitlines()[-10:])
        raise RuntimeError(f"ExifTool install failed:\n{tail}")

    installed = _resolve_command(
        "exiftool",
        [Path("/opt/homebrew/bin/exiftool"), Path("/usr/local/bin/exiftool"), Path("/usr/bin/exiftool")],
    )
    if not installed:
        raise RuntimeError("ExifTool installed but command was not found. Please reopen the app.")

    installed_checked = _resolve_exiftool_from_candidates([installed])
    if not installed_checked:
        raise RuntimeError(
            "ExifTool was installed but is not runnable on this Mac. Please reopen the app and allow install prompts."
        )

    os.environ["EXIFTOOL_PATH"] = str(installed_checked)


def _configure_runtime_env() -> None:
    root = _resource_root()
    _log(f"Resource root: {root}")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    dist_dir = root / "frontend" / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        os.environ["FRONTEND_DIST_DIR"] = str(dist_dir)

    _ensure_exiftool_available(root)


def _reuse_or_clean_existing_instance() -> bool:
    existing_pid = _read_int_file(PID_FILE)
    existing_port = _read_int_file(PORT_FILE) or PREFERRED_PORT

    if existing_pid and _is_pid_alive(existing_pid):
        if _health_ok(existing_port):
            webbrowser.open(f"http://{HOST}:{existing_port}")
            print(f"App already running on port {existing_port}.")
            return True

        _terminate_pid(existing_pid)

    _cleanup_state()
    return False


def _open_browser_when_ready(port: int) -> None:
    for _ in range(120):
        if _health_ok(port):
            webbrowser.open(f"http://{HOST}:{port}")
            return
        time.sleep(0.5)


def _stop_instance() -> None:
    pid = _read_int_file(PID_FILE)
    if not pid:
        _cleanup_state()
        _show_dialog("No running app instance found.")
        return

    if not _is_pid_alive(pid):
        _cleanup_state()
        _show_dialog("Stale app state was cleaned.")
        return

    _terminate_pid(pid)
    _cleanup_state()
    _show_dialog("App stopped.")


def _start_instance() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _log("App start requested")

    try:
        _configure_runtime_env()
    except RuntimeError as exc:
        _log(f"Runtime configuration failed: {exc}")
        _show_dialog(str(exc))
        return

    if _reuse_or_clean_existing_instance():
        _log("Reused existing healthy instance")
        return

    port = PREFERRED_PORT
    if _is_port_in_use(port):
        port = _find_free_port(PREFERRED_PORT + 1)
    _log(f"Starting backend on port {port}")

    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    PORT_FILE.write_text(str(port), encoding="utf-8")

    ready_thread = threading.Thread(target=_open_browser_when_ready, args=(port,), daemon=True)
    ready_thread.start()

    try:
        from backend.app.main import app
    except Exception as exc:
        _log(f"Backend import failed: {exc}")
        _cleanup_state()
        _show_dialog(f"Failed to load backend services: {exc}")
        return

    config = uvicorn.Config(app, host=HOST, port=port, log_level="info")
    server = uvicorn.Server(config)

    try:
        server.run()
    except Exception:
        error_trace = traceback.format_exc()
        _log(f"Uvicorn crashed:\n{error_trace}")
        _show_dialog(
            "App stopped unexpectedly. Check ~/.tracktech_metainfo_updater/launcher.log for details."
        )
    finally:
        current_pid = _read_int_file(PID_FILE)
        if current_pid == os.getpid():
            _cleanup_state()
        _log("App process finished")


def main() -> None:
    _log("Launcher opened")
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg in {"start", "--start"}:
            _start_instance()
            return
        if arg in {"stop", "--stop"}:
            _stop_instance()
            return

    action = _choose_action()
    if action == "start":
        _start_instance()
    elif action == "stop":
        _stop_instance()
    elif action == "error":
        _log("Action chooser unavailable; defaulting to start")
        _start_instance()
    else:
        _log("Launcher action canceled by user")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        error_trace = traceback.format_exc()
        _log(f"Fatal launcher error:\n{error_trace}")
        _show_dialog(
            "Launcher crashed. Check ~/.tracktech_metainfo_updater/launcher.log for details."
        )
