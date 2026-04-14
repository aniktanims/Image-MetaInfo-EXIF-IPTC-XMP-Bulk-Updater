import subprocess
import sys
from pathlib import Path
from shutil import which

from fastapi import APIRouter, HTTPException

from ..logger import get_logger
from ..models import ScanRequest, ScanResponse
from ..services.scanner import scan_folder, validate_folder_metadata

router = APIRouter(prefix="/api/scan", tags=["scan"])
logger = get_logger()


def _pick_folder_windows() -> str:
    shell = which("powershell") or which("pwsh")
    if not shell:
        return ""

    ps_script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$owner = New-Object System.Windows.Forms.Form;"
        "$owner.TopMost = $true;"
        "$owner.WindowState = [System.Windows.Forms.FormWindowState]::Minimized;"
        "$owner.ShowInTaskbar = $false;"
        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog;"
        "$dialog.Description = 'Select Photo Folder';"
        "$dialog.ShowNewFolderButton = $true;"
        "$result = $dialog.ShowDialog($owner);"
        "if ($result -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dialog.SelectedPath }"
    )
    proc = subprocess.run(
        [shell, "-STA", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode not in (0, 1):
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(stderr or "Windows folder picker failed.")

    return proc.stdout.strip()


def _pick_folder_macos() -> str:
    script = [
        "set selectedFolder to choose folder with prompt \"Select Photo Folder\"",
        "POSIX path of selectedFolder",
    ]
    command = ["osascript"]
    for line in script:
        command.extend(["-e", line])

    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode == 0:
        return proc.stdout.strip()

    stderr = (proc.stderr or "").strip()
    # User canceled the picker.
    if "User canceled" in stderr:
        return ""
    raise RuntimeError(stderr or "macOS folder picker failed.")


def _pick_folder_linux() -> str:
    if which("zenity"):
        proc = subprocess.run(
            [
                "zenity",
                "--file-selection",
                "--directory",
                "--title=Select Photo Folder",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
        if proc.returncode == 1:
            return ""
    return ""


def _pick_folder_tkinter() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return ""

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askdirectory(title="Select Photo Folder")
    root.destroy()
    return selected


def _normalize_folder_path(selected: str) -> str:
    selected = selected.strip()
    if not selected:
        return ""
    return str(Path(selected).expanduser().resolve())


@router.get("/select-folder", response_model=dict)
def select_folder() -> dict:
    selected = ""
    try:
        if sys.platform == "darwin":
            selected = _pick_folder_macos()
        elif sys.platform.startswith("win"):
            selected = _pick_folder_windows()
        else:
            selected = _pick_folder_linux()

        if not selected:
            selected = _pick_folder_tkinter()
    except Exception as exc:
        logger.error("Folder picker failed | error=%s", str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to open folder picker: {exc}") from exc

    selected = _normalize_folder_path(selected)
    if not selected:
        logger.warning("Folder selection cancelled by user")
        raise HTTPException(status_code=400, detail="Folder selection was cancelled.")

    return {"folder_path": selected}


@router.post("", response_model=ScanResponse)
def scan(payload: ScanRequest) -> ScanResponse:
    try:
        total, previews, all_files = scan_folder(payload.folder_path)
    except ValueError as exc:
        logger.error("Scan failed | folder=%s | error=%s", payload.folder_path, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ScanResponse(
        folder_path=payload.folder_path,
        total_files=total,
        matched_files=total,
        all_files=all_files,
        files=previews,
    )


@router.post("/validate", response_model=dict)
def validate_metadata(payload: ScanRequest) -> dict:
    try:
        return validate_folder_metadata(payload.folder_path)
    except ValueError as exc:
        logger.error("Validate failed | folder=%s | error=%s", payload.folder_path, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
