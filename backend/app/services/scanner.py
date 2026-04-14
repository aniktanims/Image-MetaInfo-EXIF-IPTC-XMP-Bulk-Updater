from pathlib import Path
import json
import subprocess

from ..config import SUPPORTED_EXTENSIONS
from ..models import FilePreview
from .metadata_writer import _resolve_exiftool_executable


def scan_folder(folder_path: str, preview_limit: int = 300) -> tuple[int, list[FilePreview], list[str]]:
    root = Path(folder_path)
    if not root.exists() or not root.is_dir():
        raise ValueError("Selected folder does not exist or is not a directory.")

    total = 0
    previews: list[FilePreview] = []
    all_files: list[str] = []

    for file in root.rglob("*"):
        if not file.is_file():
            continue
        ext = file.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        total += 1
        all_files.append(str(file))
        if len(previews) >= preview_limit:
            continue
        stat = file.stat()
        previews.append(
            FilePreview(
                path=str(file),
                name=file.name,
                extension=ext,
                size_bytes=stat.st_size,
            )
        )

    return total, previews, all_files


def validate_folder_metadata(folder_path: str, preview_limit: int = 200) -> dict:
    total, previews, all_files = scan_folder(folder_path)
    exiftool = _resolve_exiftool_executable()

    checked = 0
    valid_count = 0
    invalid_count = 0
    results = []

    for file_path in all_files[:preview_limit]:
        checked += 1
        command = [
            exiftool,
            "-j",
            "-DateTimeOriginal",
            "-ImageDescription",
            "-Artist",
            "-Copyright",
            "-GPSLatitude",
            "-GPSLongitude",
            "-Title",
            file_path,
        ]
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            invalid_count += 1
            results.append(
                {
                    "file_path": file_path,
                    "valid": False,
                    "issues": [proc.stderr.strip() or "Failed to read metadata"],
                    "metadata": {},
                }
            )
            continue

        data = json.loads(proc.stdout)[0]
        issues: list[str] = []
        core_present = any(
            data.get(key)
            for key in ["DateTimeOriginal", "ImageDescription", "Artist", "Copyright", "Title"]
        )
        if not core_present:
            issues.append("No core metadata fields found")

        has_lat = data.get("GPSLatitude") is not None
        has_lon = data.get("GPSLongitude") is not None
        if has_lat != has_lon:
            issues.append("GPS metadata is incomplete (latitude/longitude mismatch)")

        is_valid = len(issues) == 0
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

        results.append(
            {
                "file_path": file_path,
                "valid": is_valid,
                "issues": issues,
                "metadata": {
                    "date_taken": data.get("DateTimeOriginal"),
                    "title": data.get("Title"),
                    "description": data.get("ImageDescription"),
                    "artist": data.get("Artist"),
                    "copyright": data.get("Copyright"),
                    "gps_latitude": data.get("GPSLatitude"),
                    "gps_longitude": data.get("GPSLongitude"),
                },
            }
        )

    return {
        "folder_path": folder_path,
        "total_files": total,
        "checked_files": checked,
        "valid_files": valid_count,
        "invalid_files": invalid_count,
        "preview_limit": preview_limit,
        "preview": previews,
        "results": results,
    }
