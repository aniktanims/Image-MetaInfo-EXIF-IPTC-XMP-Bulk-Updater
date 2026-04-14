from fastapi import APIRouter, HTTPException
import subprocess

from ..logger import get_logger
from ..models import ScanRequest, ScanResponse
from ..services.scanner import scan_folder, validate_folder_metadata

router = APIRouter(prefix="/api/scan", tags=["scan"])
logger = get_logger()


@router.get("/select-folder", response_model=dict)
def select_folder() -> dict:
    selected = ""
    try:
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
            ["powershell", "-STA", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=False,
        )
        selected = proc.stdout.strip()

        if not selected:
            # Fallback to tkinter dialog if PowerShell dialog did not return a path.
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory(title="Select Photo Folder")
            root.destroy()
    except Exception as exc:
        logger.error("Folder picker failed | error=%s", str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to open folder picker: {exc}") from exc

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
