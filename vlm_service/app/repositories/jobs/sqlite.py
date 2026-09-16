"""SQLite-backed implementation of JobsRepository."""
from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from app.domain.enums import AnalysisJobStatus
from app.domain.models import AnalysisJob

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    site_path TEXT NOT NULL,
    status TEXT NOT NULL,
    total_images INTEGER NOT NULL,
    processed_images INTEGER NOT NULL,
    failed_images INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT
);
"""


def _row_to_job(row: sqlite3.Row) -> AnalysisJob:
    return AnalysisJob(
        id=row["id"],
        site_id=row["site_id"],
        site_path=row["site_path"],
        status=AnalysisJobStatus(row["status"]),
        total_images=row["total_images"],
        processed_images=row["processed_images"],
        failed_images=row["failed_images"],
        created_at=datetime.fromisoformat(row["created_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        error=row["error"],
    )


class SQLiteJobsRepository:
    def __init__(self, database_path: str) -> None:
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._database_path = database_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _add_sync(self, job: AnalysisJob) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO analysis_jobs (
                    id, site_id, site_path, status, total_images,
                    processed_images, failed_images, created_at, completed_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.site_id,
                    job.site_path,
                    job.status.value,
                    job.total_images,
                    job.processed_images,
                    job.failed_images,
                    job.created_at.isoformat(),
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.error,
                ),
            )

    def _update_sync(self, job: AnalysisJob) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE analysis_jobs SET
                    status = ?, total_images = ?, processed_images = ?,
                    failed_images = ?, completed_at = ?, error = ?
                WHERE id = ?
                """,
                (
                    job.status.value,
                    job.total_images,
                    job.processed_images,
                    job.failed_images,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.error,
                    job.id,
                ),
            )

    def _get_sync(self, job_id: str) -> AnalysisJob | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)).fetchone()
            return _row_to_job(row) if row else None

    async def add(self, job: AnalysisJob) -> None:
        await asyncio.to_thread(self._add_sync, job)

    async def get(self, job_id: str) -> AnalysisJob | None:
        return await asyncio.to_thread(self._get_sync, job_id)

    async def update(self, job: AnalysisJob) -> None:
        await asyncio.to_thread(self._update_sync, job)
