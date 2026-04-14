from __future__ import annotations

import os
import signal
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

HOST = "127.0.0.1"
PREFERRED_PORT = 8000
MAX_PORT_SCAN = 120
STATE_DIR = Path.home() / ".tracktech_metainfo_updater"
PID_FILE = STATE_DIR / "app.pid"
PORT_FILE = STATE_DIR / "app.port"


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


def _configure_runtime_env() -> None:
    root = _resource_root()

    dist_dir = root / "frontend" / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        os.environ["FRONTEND_DIST_DIR"] = str(dist_dir)

    bundled_exiftool = root / "bin" / "exiftool"
    if bundled_exiftool.exists():
        os.environ["EXIFTOOL_PATH"] = str(bundled_exiftool)


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


def main() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _configure_runtime_env()

    if _reuse_or_clean_existing_instance():
        return

    port = PREFERRED_PORT
    if _is_port_in_use(port):
        port = _find_free_port(PREFERRED_PORT + 1)
        print(f"Preferred port 8000 busy. Using port {port}.")

    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    PORT_FILE.write_text(str(port), encoding="utf-8")

    ready_thread = threading.Thread(target=_open_browser_when_ready, args=(port,), daemon=True)
    ready_thread.start()

    from backend.app.main import app

    config = uvicorn.Config(app, host=HOST, port=port, log_level="info")
    server = uvicorn.Server(config)

    try:
        server.run()
    finally:
        current_pid = _read_int_file(PID_FILE)
        if current_pid == os.getpid():
            _cleanup_state()


if __name__ == "__main__":
    main()
