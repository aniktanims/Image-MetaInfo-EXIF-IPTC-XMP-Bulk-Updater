import platform
import shutil
import subprocess

from fastapi import APIRouter, HTTPException

from ..logger import get_logger
from ..models import ScanRequest, ScanResponse
from ..services.scanner import scan_folder, validate_folder_metadata

router = APIRouter(prefix="/api/scan", tags=["scan"])
logger = get_logger()


def _pick_folder_windows() -> str:
    ps_exe = shutil.which("powershell") or shutil.which("pwsh")
    if not ps_exe:
        raise RuntimeError("PowerShell executable was not found.")

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
        [ps_exe, "-STA", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "Unknown PowerShell picker error"
        raise RuntimeError(stderr)
    return proc.stdout.strip()


def _pick_folder_macos() -> str:
    script = """
try
    set selectedFolder to choose folder with prompt \"Select Photo Folder\"
    return POSIX path of selectedFolder
on error number -128
    return \"\"
end try
""".strip()

    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if "User canceled" in stderr or "-128" in stderr:
            return ""
        raise RuntimeError(stderr or "Unknown macOS picker error")

    return proc.stdout.strip()


def _pick_folder_linux() -> str:
    zenity = shutil.which("zenity")
    if not zenity:
        raise RuntimeError("zenity is not installed.")

    proc = subprocess.run(
        [zenity, "--file-selection", "--directory", "--title=Select Photo Folder"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 1:
        # User cancelled.
        return ""
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "Unknown Linux picker error"
        raise RuntimeError(stderr)
    return proc.stdout.strip()


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
    return selected.strip()


@router.get("/select-folder", response_model=dict)
def select_folder() -> dict:
    selected = ""
    picker_error = ""
    current_os = platform.system().lower()

    try:
        if current_os == "windows":
            selected = _pick_folder_windows()
        elif current_os == "darwin":
            selected = _pick_folder_macos()
        else:
            selected = _pick_folder_linux()
    except Exception as exc:
        picker_error = str(exc)
        logger.warning("Native folder picker failed | os=%s | error=%s", current_os, picker_error)

    if not selected and (current_os != "darwin" or picker_error):
        # On macOS, empty result without error usually means user cancelled Finder.
        selected = _pick_folder_tkinter()
        if selected:
            picker_error = ""

    if not selected:
        if picker_error:
            logger.error("Folder picker failed | os=%s | error=%s", current_os, picker_error)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to open folder picker on {current_os}: {picker_error}",
            )
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
