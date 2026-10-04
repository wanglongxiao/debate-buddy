import asyncio
import hashlib
import hmac
import json
import secrets
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
    PackDetail,
    PackMessage,
    PackVersion,
    UserProfile,
)


PASSWORD_ITERATIONS = 600_000
SESSION_DAYS = 360


class UsernameExistsError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class GenerationRepository:
    def __init__(self, database_path: Path, retention_days: int = 360):
        self.database_path = Path(database_path)
        self.retention_days = retention_days

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    async def create_guest_session(
        self, *, now: Optional[datetime] = None
    ) -> tuple[UserProfile, str]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        return await asyncio.to_thread(self._create_guest_session_sync, timestamp)

    async def resolve_session(
        self, token: str, *, now: Optional[datetime] = None
    ) -> Optional[UserProfile]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        return await asyncio.to_thread(self._resolve_session_sync, token, timestamp)

    async def register(
        self,
        guest_user_id: str,
        username: str,
        password: str,
        nickname: str,
        *,
        now: Optional[datetime] = None,
    ) -> tuple[UserProfile, str]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        return await asyncio.to_thread(
            self._register_sync,
            guest_user_id,
            username,
            password,
            nickname,
            timestamp,
        )

    async def login(
        self,
        username: str,
        password: str,
        *,
        now: Optional[datetime] = None,
    ) -> tuple[UserProfile, str]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        return await asyncio.to_thread(
            self._login_sync, username, password, timestamp
        )

    async def update_profile(self, user_id: str, nickname: str) -> UserProfile:
        return await asyncio.to_thread(
            self._update_profile_sync, user_id, nickname
        )

    async def revoke_session(self, token: str) -> None:
        await asyncio.to_thread(self._revoke_session_sync, token)

    async def save(
        self,
        user_id: str,
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
            user_id,
            generation_id,
            request,
            response,
            timestamp,
        )
        return generation_id

    async def list(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        sort: str = "desc",
        query: str = "",
    ) -> HistoryListResponse:
        await self.cleanup()
        return await asyncio.to_thread(
            self._list_sync, user_id, limit, offset, sort, query
        )

    async def get(self, user_id: str, generation_id: str) -> Optional[PackDetail]:
        await self.cleanup()
        return await asyncio.to_thread(self._get_sync, user_id, generation_id)

    async def delete(self, user_id: str, generation_id: str) -> bool:
        return await asyncio.to_thread(
            self._delete_sync, user_id, generation_id
        )

    async def update_latest(
        self,
        user_id: str,
        generation_id: str,
        response: GenerateResponse,
        message: str,
        *,
        now: Optional[datetime] = None,
    ) -> bool:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        response.generation_id = generation_id
        return await asyncio.to_thread(
            self._update_latest_sync,
            user_id,
            generation_id,
            response,
            message,
            timestamp,
        )

    async def save_version(
        self,
        user_id: str,
        generation_id: str,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[PackVersion]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        return await asyncio.to_thread(
            self._save_version_sync, user_id, generation_id, timestamp
        )

    async def restore_version(
        self,
        user_id: str,
        generation_id: str,
        version_id: str,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[PackDetail]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        restored = await asyncio.to_thread(
            self._restore_version_sync,
            user_id,
            generation_id,
            version_id,
            timestamp,
        )
        if not restored:
            return None
        return await self.get(user_id, generation_id)

    async def cleanup(self, *, now: Optional[datetime] = None) -> int:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        cutoff = timestamp - timedelta(days=self.retention_days)
        return await asyncio.to_thread(self._cleanup_sync, cutoff, timestamp)

    async def count(self) -> int:
        await self.cleanup()
        return await asyncio.to_thread(self._count_sync)

    def _initialize_sync(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE COLLATE NOCASE,
                    nickname TEXT NOT NULL,
                    password_hash TEXT,
                    password_salt TEXT,
                    is_guest INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS debate_packs (
                    generation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    motion TEXT NOT NULL,
                    side TEXT NOT NULL,
                    speaker_roles_json TEXT NOT NULL,
                    language TEXT NOT NULL,
                    research_depth TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    latest_response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pack_versions (
                    version_id TEXT PRIMARY KEY,
                    generation_id TEXT NOT NULL
                        REFERENCES debate_packs(generation_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pack_messages (
                    message_id TEXT PRIMARY KEY,
                    generation_id TEXT NOT NULL
                        REFERENCES debate_packs(generation_id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user
                    ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_packs_user_updated
                    ON debate_packs(user_id, updated_at);
                CREATE INDEX IF NOT EXISTS idx_versions_pack_created
                    ON pack_versions(generation_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_messages_pack_created
                    ON pack_messages(generation_id, created_at);
                """
            )
            self._migrate_legacy_generations(connection)

    def _create_guest_session_sync(
        self, timestamp: datetime
    ) -> tuple[UserProfile, str]:
        user_id = uuid.uuid4().hex
        token = secrets.token_urlsafe(32)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    user_id, nickname, is_guest, created_at, updated_at
                ) VALUES (?, ?, 1, ?, ?)
                """,
                (user_id, "Guest", timestamp.isoformat(), timestamp.isoformat()),
            )
            self._insert_session(connection, user_id, token, timestamp)
        return UserProfile(
            user_id=user_id, nickname="Guest", is_guest=True
        ), token

    def _resolve_session_sync(
        self, token: str, timestamp: datetime
    ) -> Optional[UserProfile]:
        if not token:
            return None
        token_hash = self._token_hash(token)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT u.user_id, u.username, u.nickname, u.is_guest
                FROM sessions s
                JOIN users u ON u.user_id = s.user_id
                WHERE s.token_hash = ? AND s.expires_at > ?
                """,
                (token_hash, timestamp.isoformat()),
            ).fetchone()
        return self._profile(row) if row else None

    def _register_sync(
        self,
        guest_user_id: str,
        username: str,
        password: str,
        nickname: str,
        timestamp: datetime,
    ) -> tuple[UserProfile, str]:
        salt = secrets.token_hex(16)
        password_hash = self._password_hash(password, salt)
        token = secrets.token_urlsafe(32)
        try:
            with self._connect() as connection:
                current = connection.execute(
                    "SELECT is_guest FROM users WHERE user_id = ?",
                    (guest_user_id,),
                ).fetchone()
                if current is None or not current["is_guest"]:
                    raise InvalidCredentialsError(
                        "Only a Guest profile can be registered."
                    )
                connection.execute(
                    """
                    UPDATE users
                    SET username = ?, nickname = ?, password_hash = ?,
                        password_salt = ?, is_guest = 0, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        username,
                        nickname,
                        password_hash,
                        salt,
                        timestamp.isoformat(),
                        guest_user_id,
                    ),
                )
                connection.execute(
                    "DELETE FROM sessions WHERE user_id = ?", (guest_user_id,)
                )
                self._insert_session(
                    connection, guest_user_id, token, timestamp
                )
        except sqlite3.IntegrityError as exc:
            raise UsernameExistsError("That username is already registered.") from exc
        return UserProfile(
            user_id=guest_user_id,
            username=username,
            nickname=nickname,
            is_guest=False,
        ), token

    def _login_sync(
        self, username: str, password: str, timestamp: datetime
    ) -> tuple[UserProfile, str]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, username, nickname, password_hash,
                       password_salt, is_guest
                FROM users
                WHERE username = ? AND is_guest = 0
                """,
                (username,),
            ).fetchone()
            valid = (
                row is not None
                and row["password_salt"]
                and hmac.compare_digest(
                    row["password_hash"],
                    self._password_hash(password, row["password_salt"]),
                )
            )
            if not valid:
                raise InvalidCredentialsError("Invalid username or password.")
            token = secrets.token_urlsafe(32)
            self._insert_session(connection, row["user_id"], token, timestamp)
        return self._profile(row), token

    def _update_profile_sync(
        self, user_id: str, nickname: str
    ) -> UserProfile:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET nickname = ?, updated_at = ? WHERE user_id = ?",
                (nickname, timestamp, user_id),
            )
            row = connection.execute(
                """
                SELECT user_id, username, nickname, is_guest
                FROM users WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            raise InvalidCredentialsError("User not found.")
        return self._profile(row)

    def _revoke_session_sync(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (self._token_hash(token),),
            )

    def _save_sync(
        self,
        user_id: str,
        generation_id: str,
        request: GenerateRequest,
        response: GenerateResponse,
        created_at: datetime,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO debate_packs (
                    generation_id, user_id, motion, side, speaker_roles_json,
                    language, research_depth, request_json,
                    latest_response_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    user_id,
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
                    created_at.isoformat(),
                ),
            )

    def _list_sync(
        self,
        user_id: str,
        limit: int,
        offset: int,
        sort: str,
        query: str,
    ) -> HistoryListResponse:
        direction = "ASC" if sort == "asc" else "DESC"
        search = f"%{query.strip()}%"
        where = "user_id = ? AND motion LIKE ?"
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM debate_packs WHERE {where}",
                (user_id, search),
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT generation_id, motion, side, speaker_roles_json,
                       language, research_depth, created_at, updated_at
                FROM debate_packs
                WHERE {where}
                ORDER BY updated_at {direction}
                LIMIT ? OFFSET ?
                """,
                (user_id, search, limit, offset),
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
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    expires_at=(
                        datetime.fromisoformat(row["updated_at"])
                        + timedelta(days=self.retention_days)
                    ),
                )
                for row in rows
            ],
            total=total,
            retention_days=self.retention_days,
        )

    def _get_sync(
        self, user_id: str, generation_id: str
    ) -> Optional[PackDetail]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT request_json, latest_response_json, created_at, updated_at
                FROM debate_packs
                WHERE generation_id = ? AND user_id = ?
                """,
                (generation_id, user_id),
            ).fetchone()
            if row is None:
                return None
            version_rows = connection.execute(
                """
                SELECT version_id, name, created_at
                FROM pack_versions
                WHERE generation_id = ?
                ORDER BY created_at DESC
                """,
                (generation_id,),
            ).fetchall()
            message_rows = connection.execute(
                """
                SELECT message_id, role, content, created_at
                FROM pack_messages
                WHERE generation_id = ?
                ORDER BY created_at ASC
                """,
                (generation_id,),
            ).fetchall()
        updated_at = datetime.fromisoformat(row["updated_at"])
        response = GenerateResponse.model_validate_json(
            row["latest_response_json"]
        )
        response.generation_id = generation_id
        return PackDetail(
            generation_id=generation_id,
            request=GenerateRequest.model_validate_json(row["request_json"]),
            latest=response,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=updated_at,
            expires_at=updated_at + timedelta(days=self.retention_days),
            versions=[PackVersion(**dict(item)) for item in version_rows],
            messages=[PackMessage(**dict(item)) for item in message_rows],
        )

    def _delete_sync(self, user_id: str, generation_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM debate_packs
                WHERE generation_id = ? AND user_id = ?
                """,
                (generation_id, user_id),
            )
            return cursor.rowcount > 0

    def _update_latest_sync(
        self,
        user_id: str,
        generation_id: str,
        response: GenerateResponse,
        message: str,
        timestamp: datetime,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE debate_packs
                SET latest_response_json = ?, updated_at = ?
                WHERE generation_id = ? AND user_id = ?
                """,
                (
                    response.model_dump_json(),
                    timestamp.isoformat(),
                    generation_id,
                    user_id,
                ),
            )
            if not cursor.rowcount:
                return False
            connection.execute(
                """
                INSERT INTO pack_messages (
                    message_id, generation_id, role, content, created_at
                ) VALUES (?, ?, 'user', ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    generation_id,
                    message,
                    timestamp.isoformat(),
                ),
            )
            return True

    def _save_version_sync(
        self, user_id: str, generation_id: str, timestamp: datetime
    ) -> Optional[PackVersion]:
        version_id = uuid.uuid4().hex
        name = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        with self._connect() as connection:
            pack = connection.execute(
                """
                SELECT latest_response_json
                FROM debate_packs
                WHERE generation_id = ? AND user_id = ?
                """,
                (generation_id, user_id),
            ).fetchone()
            if pack is None:
                return None
            connection.execute(
                """
                INSERT INTO pack_versions (
                    version_id, generation_id, name, response_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    generation_id,
                    name,
                    pack["latest_response_json"],
                    timestamp.isoformat(),
                ),
            )
            connection.execute(
                """
                UPDATE debate_packs
                SET updated_at = ?
                WHERE generation_id = ? AND user_id = ?
                """,
                (timestamp.isoformat(), generation_id, user_id),
            )
            connection.execute(
                """
                DELETE FROM pack_versions
                WHERE generation_id = ?
                  AND version_id NOT IN (
                    SELECT version_id FROM pack_versions
                    WHERE generation_id = ?
                    ORDER BY created_at DESC
                    LIMIT 3
                  )
                """,
                (generation_id, generation_id),
            )
        return PackVersion(
            version_id=version_id, name=name, created_at=timestamp
        )

    @staticmethod
    def _migrate_legacy_generations(connection: sqlite3.Connection) -> None:
        legacy_table = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'generations'
            """
        ).fetchone()
        if legacy_table is None:
            return
        row_count = connection.execute(
            "SELECT COUNT(*) FROM generations"
        ).fetchone()[0]
        if row_count:
            legacy_user_id = "legacy-local-history"
            first_created = connection.execute(
                "SELECT MIN(created_at) FROM generations"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT OR IGNORE INTO users (
                    user_id, nickname, is_guest, created_at, updated_at
                ) VALUES (?, 'Legacy Guest', 1, ?, ?)
                """,
                (legacy_user_id, first_created, first_created),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO debate_packs (
                    generation_id, user_id, motion, side, speaker_roles_json,
                    language, research_depth, request_json,
                    latest_response_json, created_at, updated_at
                )
                SELECT generation_id, ?, motion, side, speaker_roles_json,
                       language, research_depth, request_json,
                       response_json, created_at, created_at
                FROM generations
                """,
                (legacy_user_id,),
            )
        connection.execute("DROP TABLE generations")

    def _restore_version_sync(
        self,
        user_id: str,
        generation_id: str,
        version_id: str,
        timestamp: datetime,
    ) -> bool:
        with self._connect() as connection:
            version = connection.execute(
                """
                SELECT v.response_json
                FROM pack_versions v
                JOIN debate_packs p ON p.generation_id = v.generation_id
                WHERE v.version_id = ? AND v.generation_id = ?
                  AND p.user_id = ?
                """,
                (version_id, generation_id, user_id),
            ).fetchone()
            if version is None:
                return False
            connection.execute(
                """
                UPDATE debate_packs
                SET latest_response_json = ?, updated_at = ?
                WHERE generation_id = ? AND user_id = ?
                """,
                (
                    version["response_json"],
                    timestamp.isoformat(),
                    generation_id,
                    user_id,
                ),
            )
            return True

    def _cleanup_sync(self, cutoff: datetime, timestamp: datetime) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM debate_packs WHERE updated_at <= ?",
                (cutoff.isoformat(),),
            )
            connection.execute(
                "DELETE FROM sessions WHERE expires_at <= ?",
                (timestamp.isoformat(),),
            )
            connection.execute(
                """
                DELETE FROM users
                WHERE is_guest = 1
                  AND user_id NOT IN (SELECT user_id FROM sessions)
                  AND user_id NOT IN (SELECT user_id FROM debate_packs)
                """
            )
            return cursor.rowcount

    def _count_sync(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM debate_packs"
                ).fetchone()[0]
            )

    @staticmethod
    def _insert_session(
        connection: sqlite3.Connection,
        user_id: str,
        token: str,
        timestamp: datetime,
    ) -> None:
        connection.execute(
            """
            INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                GenerationRepository._token_hash(token),
                user_id,
                timestamp.isoformat(),
                (timestamp + timedelta(days=SESSION_DAYS)).isoformat(),
            ),
        )

    @staticmethod
    def _profile(row: sqlite3.Row) -> UserProfile:
        return UserProfile(
            user_id=row["user_id"],
            username=row["username"],
            nickname=row["nickname"],
            is_guest=bool(row["is_guest"]),
        )

    @staticmethod
    def _password_hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            PASSWORD_ITERATIONS,
        ).hex()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

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
            connection.execute("PRAGMA foreign_keys=ON")
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
