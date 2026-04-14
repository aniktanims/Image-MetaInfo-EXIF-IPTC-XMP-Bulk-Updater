from __future__ import annotations

import shutil
import subprocess
from os import getenv
from pathlib import Path

from ..config import BACKUP_DIR
from ..models import MetadataPayload


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
    if env_path and Path(env_path).exists():
        return env_path

    on_path = shutil.which("exiftool")
    if on_path:
        return on_path

    common_paths = [
        Path.home() / "AppData/Local/Programs/ExifTool/ExifTool.exe",
        Path("C:/Program Files/ExifTool/ExifTool.exe"),
    ]
    for candidate in common_paths:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError("ExifTool executable could not be resolved.")


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

    exiftool_args = [_resolve_exiftool_executable(), *_build_exiftool_args(metadata), str(target)]

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
        raise RuntimeError(
            "ExifTool exists but is not executable. On macOS, copy the app to Applications and reopen it."
        ) from exc
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown exiftool error"
        raise RuntimeError(stderr)

    return str(target), None
