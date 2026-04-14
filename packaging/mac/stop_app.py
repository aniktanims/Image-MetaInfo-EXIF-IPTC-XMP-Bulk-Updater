from __future__ import annotations

import os
import signal
import time
from pathlib import Path

STATE_DIR = Path.home() / ".tracktech_metainfo_updater"
PID_FILE = STATE_DIR / "app.pid"
PORT_FILE = STATE_DIR / "app.port"


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _remove_state() -> None:
    for path in [PID_FILE, PORT_FILE]:
        try:
            path.unlink()
        except OSError:
            pass


def main() -> None:
    pid = _read_pid()
    if not pid:
        _remove_state()
        print("No running app instance found.")
        return

    if not _is_alive(pid):
        _remove_state()
        print("Stale app state cleaned.")
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        _remove_state()
        print("App process already stopped.")
        return

    for _ in range(25):
        if not _is_alive(pid):
            _remove_state()
            print("App stopped.")
            return
        time.sleep(0.2)

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass

    _remove_state()
    print("App force-stopped.")


if __name__ == "__main__":
    main()
