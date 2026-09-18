"""SQLite-backed implementation of ResultsRepository.

Uses the stdlib sqlite3 driver via asyncio.to_thread so the repository
interface stays async without pulling in a heavier async-SQLite dependency.
Swapping to Postgres later means writing a new class that satisfies
`app.domain.interfaces.ResultsRepository` — nothing in `services` changes.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Sequence

from app.domain.enums import InstallationStatus, WorkmanshipQuality, DevicePowerStatus,ComplianceFlags, ReviewStatus
from app.domain.models import AnalysisResult, InstallationAssessment

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_results (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    installation_status TEXT NOT NULL,
    device_power_status TEXT NOT NULL,
    workmanship_quality TEXT NOT NULL,
    compliance_flags TEXT NOT NULL,
    technical_observations TEXT NOT NULL,
    confidence REAL NOT NULL,
    raw_description TEXT NOT NULL,
    flagged_for_review INTEGER NOT NULL,
    review_status TEXT NOT NULL,
    review_notes TEXT,
    reviewed_installation_status TEXT,
    reviewed_device_power_status TEXT,
    reviewed_workmanship_quality TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_results_site_id ON analysis_results(site_id);
CREATE INDEX IF NOT EXISTS idx_results_flagged ON analysis_results(flagged_for_review);
"""


def _row_to_result(row: sqlite3.Row) -> AnalysisResult:
    assessment = InstallationAssessment(
        installation_status=InstallationStatus(row["installation_status"]),
        device_power_status=DevicePowerStatus(row["device_power_status"]),
        workmanship_quality=WorkmanshipQuality(row["workmanship_quality"]),
        compliance_flags=tuple(ComplianceFlags(mt) for mt in json.loads(row["compliance_flags"])),
        technical_observations=tuple(json.loads(row["technical_observations"])),
        confidence=row["confidence"],
        raw_description=row["raw_description"],
    )
    return AnalysisResult(
        id=row["id"],
        site_id=row["site_id"],
        image_path=row["image_path"],
        assessment=assessment,
        flagged_for_review=bool(row["flagged_for_review"]),
        review_status=ReviewStatus(row["review_status"]),
        review_notes=row["review_notes"],
        reviewed_installation_status=(
            InstallationStatus(row["reviewed_installation_status"]) if row["reviewed_installation_status"] else None
        ),
        reviewed_device_power_status=(
            InstallationStatus(row["reviewed_device_power_status"]) if row["reviewed_device_power_status"] else None
        ),
        reviewed_workmanship_quality=(
            InstallationStatus(row["reviewed_workmanship_quality"]) if row["reviewed_workmanship_quality"] else None
        ),
        reviewed_at=(
            datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None
        ),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class SQLiteResultsRepository:
    """Concrete implementation of `ResultsRepository` backed by SQLite."""

    def __init__(self, database_path: str) -> None:
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._database_path = database_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _add_sync(self, result: AnalysisResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO analysis_results (
                    id, site_id, image_path, installation_status, device_power_status,
                    workmanship_quality, compliance_flags, technical_observations,
                    confidence, raw_description, flagged_for_review, review_status,
                    review_notes, reviewed_installation_status, reviewed_device_power_status,
                    reviewed_workmanship_quality, reviewed_at,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.site_id,
                    result.image_path,
                    result.assessment.installation_status.value,
                    result.assessment.device_power_status.value,
                    result.assessment.workmanship_quality.value,
                    json.dumps([mt.value for mt in result.assessment.compliance_flags]),
                    json.dumps(list(result.assessment.technical_observations)),
                    result.assessment.confidence,
                    result.assessment.raw_description,
                    int(result.flagged_for_review),
                    result.review_status.value,
                    result.review_notes,
                    result.reviewed_installation_status.value if result.reviewed_installation_status else None,
                    result.reviewed_device_power_status.value if result.reviewed_device_power_status else None,
                    result.reviewed_workmanship_quality.value if result.reviewed_workmanship_quality else None,
                    result.reviewed_at.isoformat() if result.reviewed_at else None,
                    result.created_at.isoformat(),
                ),
            )

    def _update_sync(self, result: AnalysisResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE analysis_results SET
                    flagged_for_review = ?, review_status = ?, review_notes = ?,
                    reviewed_installation_status = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (
                    int(result.flagged_for_review),
                    result.review_status.value,
                    result.review_notes,
                    result.reviewed_installation_status.value if result.reviewed_installation_status else None,
                    result.reviewed_at.isoformat() if result.reviewed_at else None,
                    result.id,
                ),
            )

    def _get_sync(self, result_id: str) -> AnalysisResult | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_results WHERE id = ?", (result_id,)
            ).fetchone()
            return _row_to_result(row) if row else None

    def _list_by_site_sync(self, site_id: str) -> list[AnalysisResult]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analysis_results WHERE site_id = ? ORDER BY created_at DESC",
                (site_id,),
            ).fetchall()
            return [_row_to_result(r) for r in rows]

    def _list_flagged_sync(self, site_id: str | None) -> list[AnalysisResult]:
        with self._connect() as conn:
            if site_id:
                rows = conn.execute(
                    "SELECT * FROM analysis_results WHERE flagged_for_review = 1 "
                    "AND review_status = ? AND site_id = ? ORDER BY created_at DESC",
                    (ReviewStatus.PENDING.value, site_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM analysis_results WHERE flagged_for_review = 1 "
                    "AND review_status = ? ORDER BY created_at DESC",
                    (ReviewStatus.PENDING.value,),
                ).fetchall()
            return [_row_to_result(r) for r in rows]

    async def add(self, result: AnalysisResult) -> None:
        await asyncio.to_thread(self._add_sync, result)

    async def get(self, result_id: str) -> AnalysisResult | None:
        return await asyncio.to_thread(self._get_sync, result_id)

    async def list_by_site(self, site_id: str) -> Sequence[AnalysisResult]:
        return await asyncio.to_thread(self._list_by_site_sync, site_id)

    async def list_flagged(self, site_id: str | None = None) -> Sequence[AnalysisResult]:
        return await asyncio.to_thread(self._list_flagged_sync, site_id)

    async def update(self, result: AnalysisResult) -> None:
        await asyncio.to_thread(self._update_sync, result)
