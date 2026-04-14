from __future__ import annotations

import os
import shutil
import subprocess
from os import getenv
from pathlib import Path

from ..config import BACKUP_DIR
from ..models import MetadataPayload

RUNTIME_BIN_DIR = Path.home() / ".tracktech_metainfo_updater" / "bin"


def _unique_target(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_exiftool_executable() -> str:
    env_path = getenv("EXIFTOOL_PATH")
    if env_path:
        env_candidate = Path(env_path)
        if env_candidate.exists() and _can_run_exiftool(env_candidate):
            return str(env_candidate)
        repaired = _repair_exiftool_binary(env_candidate)
        if repaired:
            return str(repaired)

    on_path = shutil.which("exiftool")
    if on_path and _can_run_exiftool(Path(on_path)):
        return on_path

    common_paths = [
        Path.home() / "AppData/Local/Programs/ExifTool/ExifTool.exe",
        Path("C:/Program Files/ExifTool/ExifTool.exe"),
        Path("/opt/homebrew/bin/exiftool"),
        Path("/usr/local/bin/exiftool"),
        Path("/usr/bin/exiftool"),
    ]
    for candidate in common_paths:
        if candidate.exists() and _can_run_exiftool(candidate):
            return str(candidate)

        repaired = _repair_exiftool_binary(candidate)
        if repaired:
            return str(repaired)

    raise FileNotFoundError("ExifTool executable could not be resolved.")


def _read_exiftool_version(path: Path) -> str | None:
    try:
        result = subprocess.run(
            [str(path), "-ver"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    version = (result.stdout or "").strip().splitlines()
    return version[0].strip() if version else None


def _can_run_exiftool(path: Path) -> bool:
    if not path.exists():
        return False

    if not os.access(path, os.X_OK):
        try:
            path.chmod(path.stat().st_mode | 0o111)
        except OSError:
            return False

    return _read_exiftool_version(path) is not None


def get_exiftool_status() -> dict:
    try:
        executable = _resolve_exiftool_executable()
    except Exception as exc:
        return {
            "available": False,
            "path": None,
            "version": None,
            "error": str(exc),
        }

    version = _read_exiftool_version(Path(executable))
    if not version:
        return {
            "available": False,
            "path": executable,
            "version": None,
            "error": "ExifTool was found but version check failed.",
        }

    return {
        "available": True,
        "path": executable,
        "version": version,
        "error": None,
    }


def _repair_exiftool_binary(path: Path) -> Path | None:
    if not path.exists():
        return None

    try:
        path.chmod(path.stat().st_mode | 0o111)
    except OSError:
        pass

    if _can_run_exiftool(path):
        return path

    try:
        RUNTIME_BIN_DIR.mkdir(parents=True, exist_ok=True)
        staged = RUNTIME_BIN_DIR / "exiftool"
        shutil.copy2(path, staged)
        staged.chmod(0o755)
    except OSError:
        return None

    if _can_run_exiftool(staged):
        return staged

    return None


def _build_exiftool_args(metadata: MetadataPayload) -> list[str]:
    args: list[str] = ["-overwrite_original"]

    if metadata.date_taken:
        args.append(f"-DateTimeOriginal={metadata.date_taken}")
        args.append(f"-CreateDate={metadata.date_taken}")
    if metadata.title:
        args.append(f"-Title={metadata.title}")
        args.append(f"-ObjectName={metadata.title}")
        args.append(f"-XMP-dc:Title={metadata.title}")
        args.append(f"-XMP-photoshop:Headline={metadata.title}")
    if metadata.description:
        args.append(f"-ImageDescription={metadata.description}")
        args.append(f"-XMP-dc:Description={metadata.description}")
        args.append(f"-Caption-Abstract={metadata.description}")
    if metadata.comment:
        args.append(f"-Comment={metadata.comment}")
        args.append(f"-UserComment={metadata.comment}")
    if metadata.headline:
        args.append(f"-Headline={metadata.headline}")
        args.append(f"-XMP-photoshop:Headline={metadata.headline}")
    if metadata.artist:
        args.append(f"-Artist={metadata.artist}")
        args.append(f"-By-line={metadata.artist}")
        args.append(f"-XMP-dc:Creator={metadata.artist}")
    if metadata.credit:
        args.append(f"-Credit={metadata.credit}")
        args.append(f"-XMP-photoshop:Credit={metadata.credit}")
    if metadata.source:
        args.append(f"-Source={metadata.source}")
        args.append(f"-XMP-photoshop:Source={metadata.source}")
    if metadata.instructions:
        args.append(f"-SpecialInstructions={metadata.instructions}")
        args.append(f"-XMP-photoshop:Instructions={metadata.instructions}")
    if metadata.copyright_text:
        args.append(f"-Copyright={metadata.copyright_text}")
        args.append(f"-CopyrightNotice={metadata.copyright_text}")
        args.append(f"-XMP-dc:Rights={metadata.copyright_text}")
    if metadata.software:
        args.append(f"-Software={metadata.software}")
        args.append(f"-XMP-xmp:CreatorTool={metadata.software}")
    if metadata.rating is not None:
        rating = max(0, min(5, int(metadata.rating)))
        args.append(f"-Rating={rating}")
        args.append(f"-XMP-xmp:Rating={rating}")

    if metadata.keywords:
        args.append("-IPTC:Keywords=")
        args.append("-XMP-dc:Subject=")
        for keyword in metadata.keywords:
            args.append(f"-IPTC:Keywords+={keyword}")
            args.append(f"-XMP-dc:Subject+={keyword}")

    if metadata.gps_latitude is not None and metadata.gps_longitude is not None:
        if not (-90 <= metadata.gps_latitude <= 90):
            raise ValueError("GPS latitude must be between -90 and 90.")
        if not (-180 <= metadata.gps_longitude <= 180):
            raise ValueError("GPS longitude must be between -180 and 180.")

        lat_ref = "N" if metadata.gps_latitude >= 0 else "S"
        lon_ref = "E" if metadata.gps_longitude >= 0 else "W"
        lat_abs = abs(metadata.gps_latitude)
        lon_abs = abs(metadata.gps_longitude)

        # Write both EXIF and XMP GPS tags to maximize compatibility across Apple/Google Photos.
        args.append(f"-GPSLatitudeRef={lat_ref}")
        args.append(f"-GPSLatitude={lat_abs}")
        args.append(f"-GPSLongitudeRef={lon_ref}")
        args.append(f"-GPSLongitude={lon_abs}")
        args.append(f"-XMP-exif:GPSLatitude={lat_abs}")
        args.append(f"-XMP-exif:GPSLongitude={lon_abs}")
        args.append(f"-XMP-exif:GPSLatitudeRef={lat_ref}")
        args.append(f"-XMP-exif:GPSLongitudeRef={lon_ref}")

    if metadata.location_name:
        args.append(f"-Sub-location={metadata.location_name}")
        args.append(f"-XMP-iptcCore:Location={metadata.location_name}")
    if metadata.city:
        args.append(f"-City={metadata.city}")
        args.append(f"-XMP-photoshop:City={metadata.city}")
    if metadata.state:
        args.append(f"-Province-State={metadata.state}")
        args.append(f"-XMP-photoshop:State={metadata.state}")
    if metadata.country:
        args.append(f"-Country-PrimaryLocationName={metadata.country}")
        args.append(f"-XMP-photoshop:Country={metadata.country}")
    if metadata.country_code:
        args.append(f"-Country-PrimaryLocationCode={metadata.country_code}")
        args.append(f"-XMP-iptcCore:CountryCode={metadata.country_code}")
    if metadata.contact_email:
        args.append(f"-XMP-iptcCore:CreatorWorkEmail={metadata.contact_email}")
    if metadata.contact_url:
        args.append(f"-XMP-iptcCore:CreatorWorkURL={metadata.contact_url}")

    for key, value in metadata.custom_fields.items():
        args.append(f"-XMP-{key}={value}")

    return args


def write_metadata(
    file_path: str,
    metadata: MetadataPayload,
    write_mode: str,
    output_folder: str | None,
) -> tuple[str, str | None]:
    source = Path(file_path)
    if not source.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    target = source
    if write_mode == "output_folder":
        if not output_folder:
            raise ValueError("Output folder is required for output_folder mode.")
        out_dir = Path(output_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        target = _unique_target(out_dir / source.name)
        shutil.copy2(source, target)
    else:
        backup_dir = BACKUP_DIR / source.parent.name
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup_dir / source.name)

    exiftool_executable = _resolve_exiftool_executable()
    exiftool_args = [exiftool_executable, *_build_exiftool_args(metadata), str(target)]

    try:
        result = subprocess.run(
            exiftool_args,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ExifTool is not installed or not on PATH. Install ExifTool and retry."
        ) from exc
    except PermissionError as exc:
        repaired = _repair_exiftool_binary(Path(exiftool_executable))
        if repaired:
            exiftool_args[0] = str(repaired)
            result = subprocess.run(
                exiftool_args,
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            raise RuntimeError(
                "ExifTool exists but is not executable. Please allow install when prompted, then reopen the app."
            ) from exc
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown exiftool error"
        raise RuntimeError(stderr)

    return str(target), None
