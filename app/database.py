import asyncio
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

from app.models import (
    GenerateRequest,
    GenerateResponse,
    HistoryItem,
    HistoryListResponse,
)


class GenerationRepository:
    def __init__(self, database_path: Path, retention_days: int = 30):
        self.database_path = Path(database_path)
        self.retention_days = retention_days

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    async def save(
        self,
        request: GenerateRequest,
        response: GenerateResponse,
        *,
        now: Optional[datetime] = None,
    ) -> str:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        await self.cleanup(now=timestamp)
        generation_id = uuid.uuid4().hex
        response.generation_id = generation_id
        await asyncio.to_thread(
            self._save_sync,
            generation_id,
            request,
            response,
            timestamp,
        )
        return generation_id

    async def list(self, limit: int = 20, offset: int = 0) -> HistoryListResponse:
        await self.cleanup()
        return await asyncio.to_thread(self._list_sync, limit, offset)

    async def get(self, generation_id: str) -> Optional[GenerateResponse]:
        await self.cleanup()
        return await asyncio.to_thread(self._get_sync, generation_id)

    async def delete(self, generation_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, generation_id)

    async def cleanup(self, *, now: Optional[datetime] = None) -> int:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        cutoff = timestamp - timedelta(days=self.retention_days)
        return await asyncio.to_thread(self._cleanup_sync, cutoff)

    async def count(self) -> int:
        await self.cleanup()
        return await asyncio.to_thread(self._count_sync)

    def _initialize_sync(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generations (
                    generation_id TEXT PRIMARY KEY,
                    motion TEXT NOT NULL,
                    side TEXT NOT NULL,
                    speaker_roles_json TEXT NOT NULL,
                    language TEXT NOT NULL,
                    research_depth TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_generations_created_at
                ON generations(created_at)
                """
            )

    def _save_sync(
        self,
        generation_id: str,
        request: GenerateRequest,
        response: GenerateResponse,
        created_at: datetime,
    ) -> None:
        expires_at = created_at + timedelta(days=self.retention_days)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generations (
                    generation_id,
                    motion,
                    side,
                    speaker_roles_json,
                    language,
                    research_depth,
                    request_json,
                    response_json,
                    created_at,
                    expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    request.motion,
                    request.side.value,
                    json.dumps(
                        [role.value for role in request.speaker_roles],
                        ensure_ascii=False,
                    ),
                    request.language.value,
                    request.research_depth.value,
                    request.model_dump_json(),
                    response.model_dump_json(),
                    created_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def _list_sync(self, limit: int, offset: int) -> HistoryListResponse:
        with self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM generations"
            ).fetchone()[0]
            rows = connection.execute(
                """
                SELECT generation_id, motion, side, speaker_roles_json,
                       language, research_depth, created_at, expires_at
                FROM generations
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return HistoryListResponse(
            items=[
                HistoryItem(
                    generation_id=row["generation_id"],
                    motion=row["motion"],
                    side=row["side"],
                    speaker_roles=json.loads(row["speaker_roles_json"]),
                    language=row["language"],
                    research_depth=row["research_depth"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]),
                )
                for row in rows
            ],
            total=total,
            retention_days=self.retention_days,
        )

    def _get_sync(self, generation_id: str) -> Optional[GenerateResponse]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT response_json
                FROM generations
                WHERE generation_id = ?
                """,
                (generation_id,),
            ).fetchone()
        if row is None:
            return None
        response = GenerateResponse.model_validate_json(row["response_json"])
        response.generation_id = generation_id
        return response

    def _delete_sync(self, generation_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM generations WHERE generation_id = ?",
                (generation_id,),
            )
            return cursor.rowcount > 0

    def _cleanup_sync(self, cutoff: datetime) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM generations WHERE created_at <= ?",
                (cutoff.isoformat(),),
            )
            return cursor.rowcount

    def _count_sync(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.database_path,
            timeout=5,
            isolation_level="DEFERRED",
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=5000")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
