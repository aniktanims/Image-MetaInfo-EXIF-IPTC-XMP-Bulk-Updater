from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    folder_path: str


class FilePreview(BaseModel):
    path: str
    name: str
    extension: str
    size_bytes: int


class ScanResponse(BaseModel):
    folder_path: str
    total_files: int
    matched_files: int
    all_files: list[str]
    files: list[FilePreview]


class MetadataPayload(BaseModel):
    date_taken: str | None = None
    title: str | None = None
    description: str | None = None
    comment: str | None = None
    headline: str | None = None
    keywords: list[str] = Field(default_factory=list)
    artist: str | None = None
    credit: str | None = None
    source: str | None = None
    instructions: str | None = None
    copyright_text: str | None = None
    software: str | None = None
    rating: int | None = None
    location_name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    country_code: str | None = None
    postal_code: str | None = None
    contact_email: str | None = None
    contact_url: str | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    custom_fields: dict[str, str] = Field(default_factory=dict)


class JobCreateRequest(BaseModel):
    files: list[str]
    metadata: MetadataPayload
    write_mode: Literal["overwrite", "output_folder"]
    output_folder: str | None = None
    filename_prefix: str | None = None
    filename_start_index: int = Field(default=1, ge=1)
    filename_number_position: Literal["suffix", "prefix"] = "suffix"


class JobSummary(BaseModel):
    job_id: str
    status: Literal["pending", "running", "paused", "completed", "failed", "cancelled"]
    total_files: int
    processed_files: int
    failed_files: int
    started_at: datetime | None
    completed_at: datetime | None


class JobResultItem(BaseModel):
    file_path: str
    status: Literal["completed", "failed", "skipped"]
    error: str | None = None
    output_path: str | None = None


class JobStatusResponse(BaseModel):
    summary: JobSummary
    results: list[JobResultItem] = Field(default_factory=list)


class ProgressEvent(BaseModel):
    event: Literal["progress", "completed", "failed", "cancelled"]
    job_id: str
    processed_files: int
    total_files: int
    failed_files: int
    current_file: str | None = None
    message: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
