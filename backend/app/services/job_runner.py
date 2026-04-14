from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from ..database import get_connection, now_iso
from ..logger import get_logger
from ..models import JobCreateRequest, JobResultItem, JobSummary
from .metadata_writer import write_metadata
from .progress_hub import progress_hub


class JobRunner:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._jobs_cancelled: set[str] = set()
        self._logger = get_logger()
        self._batch_size = 100
        self._retry_attempts = 2

    async def create_job(self, payload: JobCreateRequest) -> str:
        unresolved = self._load_unresolved_failures()
        unresolved_existing = [path for path in unresolved if Path(path).exists()]
        if unresolved_existing:
            deduped = dict.fromkeys([*payload.files, *unresolved_existing])
            payload.files = list(deduped.keys())
            self._logger.info("Loaded unresolved failed files into new job | count=%s", len(unresolved_existing))

        if payload.write_mode == "output_folder" and not payload.output_folder:
            payload.output_folder = self._create_default_output_folder(payload.files)
            self._logger.info(
                "Auto-created output folder for job request | output_folder=%s",
                payload.output_folder,
            )

        job_id = str(uuid.uuid4())
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO jobs (id, status, write_mode, output_folder, total_files, processed_files, failed_files, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, ?, NULL)
                """,
                (
                    job_id,
                    "pending",
                    payload.write_mode,
                    payload.output_folder,
                    len(payload.files),
                    now_iso(),
                ),
            )
            connection.commit()

        asyncio.create_task(self._run_job(job_id, payload))
        self._logger.info(
            "Job created | job_id=%s | files=%s | write_mode=%s | output_folder=%s",
            job_id,
            len(payload.files),
            payload.write_mode,
            payload.output_folder,
        )
        return job_id

    def _create_default_output_folder(self, files: list[str]) -> str:
        if not files:
            raise ValueError("Cannot create output folder without files.")
        first_parent = Path(files[0]).resolve().parent
        folder_name = f"MetaINFO_Output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_path = first_parent / folder_name
        output_path.mkdir(parents=True, exist_ok=True)
        return str(output_path)

    async def _run_job(self, job_id: str, payload: JobCreateRequest) -> None:
        self._set_status(job_id, "running")
        self._logger.info("Job started | job_id=%s", job_id)
        processed = 0
        failed = 0
        total_files = len(payload.files)

        for index, file_path in enumerate(payload.files):
            if job_id in self._jobs_cancelled:
                self._set_status(job_id, "cancelled", completed=True)
                self._logger.warning("Job cancelled | job_id=%s | processed=%s | failed=%s", job_id, processed, failed)
                await progress_hub.broadcast(
                    job_id,
                    {
                        "event": "cancelled",
                        "job_id": job_id,
                        "processed_files": processed,
                        "total_files": total_files,
                        "failed_files": failed,
                        "message": "Job cancelled by user.",
                    },
                )
                return

            target_output_folder = self._resolve_output_folder_for_index(payload, index)
            file_error: Exception | None = None
            try:
                output_path = None
                for attempt in range(self._retry_attempts + 1):
                    try:
                        output_path, _ = await asyncio.get_running_loop().run_in_executor(
                            self._executor,
                            write_metadata,
                            file_path,
                            payload.metadata,
                            payload.write_mode,
                            target_output_folder,
                        )
                        break
                    except Exception as exc:
                        file_error = exc
                        if attempt < self._retry_attempts:
                            self._logger.warning(
                                "Retrying failed file | job_id=%s | file=%s | attempt=%s | error=%s",
                                job_id,
                                file_path,
                                attempt + 1,
                                str(exc),
                            )
                if output_path is None and file_error is not None:
                    raise file_error

                self._save_result(job_id, file_path, "completed", None, output_path)
                self._mark_failure_resolved(file_path)
            except Exception as exc:
                failed += 1
                self._save_result(job_id, file_path, "failed", str(exc), None)
                self._mark_failure_unresolved(file_path, str(exc))
                self._logger.error(
                    "File processing failed | job_id=%s | file=%s | error=%s",
                    job_id,
                    file_path,
                    str(exc),
                )

            processed += 1
            self._update_counts(job_id, processed, failed)
            await progress_hub.broadcast(
                job_id,
                {
                    "event": "progress",
                    "job_id": job_id,
                    "processed_files": processed,
                    "total_files": total_files,
                    "failed_files": failed,
                    "current_file": file_path,
                    "extra": {
                        "batch_index": (index // self._batch_size) + 1,
                        "batch_size": self._batch_size,
                    },
                },
            )

        final_status = "failed" if failed == total_files and processed > 0 else "completed"
        self._set_status(job_id, final_status, completed=True)
        self._logger.info(
            "Job finished | job_id=%s | status=%s | processed=%s | failed=%s",
            job_id,
            final_status,
            processed,
            failed,
        )
        await progress_hub.broadcast(
            job_id,
            {
                "event": "completed" if final_status == "completed" else "failed",
                "job_id": job_id,
                "processed_files": processed,
                "total_files": total_files,
                "failed_files": failed,
                "message": "Job finished.",
            },
        )

    def _resolve_output_folder_for_index(self, payload: JobCreateRequest, file_index: int) -> str | None:
        if payload.write_mode != "output_folder":
            return payload.output_folder

        if not payload.output_folder:
            return None

        if len(payload.files) <= self._batch_size:
            return payload.output_folder

        source_name = Path(payload.files[file_index]).resolve().parent.name
        batch_number = (file_index // self._batch_size) + 1
        batch_folder = Path(payload.output_folder) / f"Batch {batch_number} - {source_name}"
        batch_folder.mkdir(parents=True, exist_ok=True)
        return str(batch_folder)

    def _load_unresolved_failures(self) -> list[str]:
        with get_connection() as connection:
            cursor = connection.cursor()
            rows = cursor.execute(
                """
                SELECT file_path
                FROM unresolved_failures
                WHERE resolved = 0
                ORDER BY last_seen_at ASC
                """
            ).fetchall()
        return [row[0] for row in rows]

    def _mark_failure_unresolved(self, file_path: str, error: str) -> None:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO unresolved_failures (file_path, last_error, retry_count, resolved, last_seen_at)
                VALUES (?, ?, 1, 0, ?)
                ON CONFLICT(file_path)
                DO UPDATE SET
                    last_error = excluded.last_error,
                    retry_count = unresolved_failures.retry_count + 1,
                    resolved = 0,
                    last_seen_at = excluded.last_seen_at
                """,
                (file_path, error, now_iso()),
            )
            connection.commit()

    def _mark_failure_resolved(self, file_path: str) -> None:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE unresolved_failures
                SET resolved = 1,
                    last_seen_at = ?
                WHERE file_path = ?
                """,
                (now_iso(), file_path),
            )
            connection.commit()

    def cancel_job(self, job_id: str) -> None:
        self._jobs_cancelled.add(job_id)

    def get_summary(self, job_id: str) -> JobSummary:
        with get_connection() as connection:
            connection.row_factory = lambda cursor, row: {
                "id": row[0],
                "status": row[1],
                "total_files": row[2],
                "processed_files": row[3],
                "failed_files": row[4],
                "started_at": row[5],
                "completed_at": row[6],
            }
            cursor = connection.cursor()
            row = cursor.execute(
                """
                SELECT id, status, total_files, processed_files, failed_files, started_at, completed_at
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
            if not row:
                raise ValueError("Job not found.")

        return JobSummary(
            job_id=row["id"],
            status=row["status"],
            total_files=row["total_files"],
            processed_files=row["processed_files"],
            failed_files=row["failed_files"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    def get_results(self, job_id: str) -> list[JobResultItem]:
        with get_connection() as connection:
            cursor = connection.cursor()
            rows = cursor.execute(
                """
                SELECT file_path, status, error, output_path
                FROM job_results
                WHERE job_id = ?
                ORDER BY id ASC
                """,
                (job_id,),
            ).fetchall()

        return [
            JobResultItem(file_path=row[0], status=row[1], error=row[2], output_path=row[3])
            for row in rows
        ]

    def _save_result(
        self,
        job_id: str,
        file_path: str,
        status: str,
        error: str | None,
        output_path: str | None,
    ) -> None:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO job_results (job_id, file_path, status, error, output_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, file_path, status, error, output_path, now_iso()),
            )
            connection.commit()

    def _update_counts(self, job_id: str, processed: int, failed: int) -> None:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET processed_files = ?, failed_files = ?
                WHERE id = ?
                """,
                (processed, failed, job_id),
            )
            connection.commit()

    def _set_status(self, job_id: str, status: str, completed: bool = False) -> None:
        completed_at = now_iso() if completed else None
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = ?, completed_at = COALESCE(?, completed_at)
                WHERE id = ?
                """,
                (status, completed_at, job_id),
            )
            connection.commit()


job_runner = JobRunner()
