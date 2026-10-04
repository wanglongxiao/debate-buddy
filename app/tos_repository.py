from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from urllib.parse import urlsplit, urlunsplit

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.database import (
    PASSWORD_ITERATIONS,
    SESSION_DAYS,
    InvalidCredentialsError,
    UsernameExistsError,
)
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


class TosGenerationRepository:
    """TOS-backed repository using BytePlus's S3-compatible API."""

    LIFECYCLE_RULE_ID = "debate-buddy-expire-packs"
    SESSION_LIFECYCLE_RULE_ID = "debate-buddy-expire-sessions"

    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        endpoint: str,
        region: str,
        bucket: str,
        prefix: str = "debate-buddy/v1",
        retention_days: int = 360,
        client: Any = None,
    ):
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.retention_days = retention_days
        self.client = client or boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=self._s3_endpoint(endpoint),
            region_name=region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
                retries={"max_attempts": 4, "mode": "standard"},
            ),
        )
        self.region = region

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
        return await asyncio.to_thread(self._login_sync, username, password, timestamp)

    async def update_profile(self, user_id: str, nickname: str) -> UserProfile:
        return await asyncio.to_thread(self._update_profile_sync, user_id, nickname)

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
        generation_id = uuid.uuid4().hex
        response.generation_id = generation_id
        payload = {
            "schema_version": 1,
            "generation_id": generation_id,
            "user_id": user_id,
            "request": request.model_dump(mode="json"),
            "latest": response.model_dump(mode="json"),
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
            "versions": [],
            "messages": [],
        }
        await asyncio.to_thread(
            self._put_json,
            self._pack_key(user_id, generation_id),
            payload,
            None,
            True,
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
        return await asyncio.to_thread(
            self._list_sync, user_id, limit, offset, sort, query
        )

    async def get(self, user_id: str, generation_id: str) -> Optional[PackDetail]:
        return await asyncio.to_thread(self._get_sync, user_id, generation_id)

    async def delete(self, user_id: str, generation_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, user_id, generation_id)

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

        def update(pack: dict[str, Any]) -> None:
            pack["latest"] = response.model_dump(mode="json")
            pack["updated_at"] = timestamp.isoformat()
            pack.setdefault("messages", []).append(
                {
                    "message_id": uuid.uuid4().hex,
                    "role": "user",
                    "content": message,
                    "created_at": timestamp.isoformat(),
                }
            )

        return await asyncio.to_thread(
            self._update_pack_sync, user_id, generation_id, update
        )

    async def save_version(
        self,
        user_id: str,
        generation_id: str,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[PackVersion]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        version = PackVersion(
            version_id=uuid.uuid4().hex,
            name=timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            created_at=timestamp,
        )

        def update(pack: dict[str, Any]) -> None:
            versions = pack.setdefault("versions", [])
            versions.insert(
                0,
                {
                    **version.model_dump(mode="json"),
                    "response": pack["latest"],
                },
            )
            del versions[3:]
            pack["updated_at"] = timestamp.isoformat()

        updated = await asyncio.to_thread(
            self._update_pack_sync, user_id, generation_id, update
        )
        return version if updated else None

    async def restore_version(
        self,
        user_id: str,
        generation_id: str,
        version_id: str,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[PackDetail]:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        found = False

        def update(pack: dict[str, Any]) -> None:
            nonlocal found
            version = next(
                (
                    item
                    for item in pack.get("versions", [])
                    if item["version_id"] == version_id
                ),
                None,
            )
            if version is not None:
                pack["latest"] = version["response"]
                pack["updated_at"] = timestamp.isoformat()
                found = True

        updated = await asyncio.to_thread(
            self._update_pack_sync, user_id, generation_id, update
        )
        if not updated or not found:
            return None
        return await self.get(user_id, generation_id)

    async def cleanup(self, *, now: Optional[datetime] = None) -> int:
        timestamp = self._as_utc(now or datetime.now(timezone.utc))
        return await asyncio.to_thread(self._cleanup_sync, timestamp)

    async def count(self) -> int:
        return await asyncio.to_thread(
            lambda: len(self._list_keys(self._key("packs/")))
        )

    def _initialize_sync(self) -> None:
        self.client.head_bucket(Bucket=self.bucket)
        acl = self.client.get_bucket_acl(Bucket=self.bucket)
        public_uris = {
            "http://acs.amazonaws.com/groups/global/AllUsers",
            "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
        }
        if any(
            grant.get("Grantee", {}).get("URI") in public_uris
            for grant in acl.get("Grants", [])
        ):
            raise RuntimeError("The TOS bucket must not grant public access.")

        lifecycle = self.client.get_bucket_lifecycle_configuration(
            Bucket=self.bucket
        ).get("Rules", [])
        expected = {
            self.LIFECYCLE_RULE_ID: self._key("packs/"),
            self.SESSION_LIFECYCLE_RULE_ID: self._key("sessions/"),
        }
        configured = {}
        for rule in lifecycle:
            prefix = rule.get("Prefix") or rule.get("Filter", {}).get("Prefix")
            if (
                rule.get("Status") == "Enabled"
                and rule.get("Expiration", {}).get("Days") == self.retention_days
            ):
                configured[rule.get("ID")] = prefix
        if any(
            configured.get(rule_id) != prefix for rule_id, prefix in expected.items()
        ):
            raise RuntimeError(
                "The TOS bucket is missing the required private 360-day "
                "lifecycle configuration."
            )

    def _create_guest_session_sync(
        self, timestamp: datetime
    ) -> tuple[UserProfile, str]:
        user_id = uuid.uuid4().hex
        token = secrets.token_urlsafe(32)
        token_hash = self._token_hash(token)
        user = {
            "user_id": user_id,
            "username": None,
            "nickname": "Guest",
            "password_hash": None,
            "password_salt": None,
            "is_guest": True,
            "session_hashes": [token_hash],
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
        }
        self._put_json(self._user_key(user_id), user, if_none_match=True)
        self._put_session(token_hash, user_id, timestamp)
        return self._profile(user), token

    def _resolve_session_sync(
        self, token: str, timestamp: datetime
    ) -> Optional[UserProfile]:
        if not token:
            return None
        token_hash = self._token_hash(token)
        session, _ = self._get_json(self._session_key(token_hash))
        if session is None:
            return None
        if datetime.fromisoformat(session["expires_at"]) <= timestamp:
            self.client.delete_object(
                Bucket=self.bucket, Key=self._session_key(token_hash)
            )
            return None
        user, _ = self._get_json(self._user_key(session["user_id"]))
        if user is None or token_hash not in user.get("session_hashes", []):
            return None
        return self._profile(user)

    def _register_sync(
        self,
        guest_user_id: str,
        username: str,
        password: str,
        nickname: str,
        timestamp: datetime,
    ) -> tuple[UserProfile, str]:
        user_key = self._user_key(guest_user_id)
        user, etag = self._get_json(user_key)
        if user is None or not user.get("is_guest"):
            raise InvalidCredentialsError("Only a Guest profile can be registered.")
        username_key = self._username_key(username)
        try:
            self._put_json(
                username_key,
                {"username": username, "user_id": guest_user_id},
                if_none_match=True,
            )
        except ClientError as exc:
            if self._is_precondition_error(exc):
                raise UsernameExistsError(
                    "That username is already registered."
                ) from exc
            raise

        salt = secrets.token_hex(16)
        token = secrets.token_urlsafe(32)
        token_hash = self._token_hash(token)
        user.update(
            {
                "username": username,
                "nickname": nickname,
                "password_hash": self._password_hash(password, salt),
                "password_salt": salt,
                "is_guest": False,
                "session_hashes": [token_hash],
                "updated_at": timestamp.isoformat(),
            }
        )
        try:
            self._put_json(user_key, user, if_match=etag)
        except Exception:
            self.client.delete_object(Bucket=self.bucket, Key=username_key)
            raise
        self._put_session(token_hash, guest_user_id, timestamp)
        return self._profile(user), token

    def _login_sync(
        self, username: str, password: str, timestamp: datetime
    ) -> tuple[UserProfile, str]:
        index, _ = self._get_json(self._username_key(username))
        if index is None:
            raise InvalidCredentialsError("Invalid username or password.")
        user_key = self._user_key(index["user_id"])
        token = secrets.token_urlsafe(32)
        token_hash = self._token_hash(token)

        for _ in range(4):
            user, etag = self._get_json(user_key)
            valid = (
                user is not None
                and not user.get("is_guest")
                and user.get("password_salt")
                and hmac.compare_digest(
                    user.get("password_hash", ""),
                    self._password_hash(password, user["password_salt"]),
                )
            )
            if not valid:
                raise InvalidCredentialsError("Invalid username or password.")
            sessions = list(dict.fromkeys(user.get("session_hashes", [])))
            sessions.append(token_hash)
            user["session_hashes"] = sessions[-20:]
            user["updated_at"] = timestamp.isoformat()
            try:
                self._put_json(user_key, user, if_match=etag)
                break
            except ClientError as exc:
                if not self._is_precondition_error(exc):
                    raise
        else:
            raise RuntimeError("Could not update the user session safely.")
        self._put_session(token_hash, user["user_id"], timestamp)
        return self._profile(user), token

    def _update_profile_sync(self, user_id: str, nickname: str) -> UserProfile:
        timestamp = datetime.now(timezone.utc)
        user_key = self._user_key(user_id)
        for _ in range(4):
            user, etag = self._get_json(user_key)
            if user is None:
                raise InvalidCredentialsError("User not found.")
            user["nickname"] = nickname
            user["updated_at"] = timestamp.isoformat()
            try:
                self._put_json(user_key, user, if_match=etag)
                return self._profile(user)
            except ClientError as exc:
                if not self._is_precondition_error(exc):
                    raise
        raise RuntimeError("Could not update the profile safely.")

    def _revoke_session_sync(self, token: str) -> None:
        token_hash = self._token_hash(token)
        session_key = self._session_key(token_hash)
        session, _ = self._get_json(session_key)
        if session is not None:
            user_key = self._user_key(session["user_id"])
            for _ in range(4):
                user, etag = self._get_json(user_key)
                if user is None:
                    break
                user["session_hashes"] = [
                    item
                    for item in user.get("session_hashes", [])
                    if item != token_hash
                ]
                try:
                    self._put_json(user_key, user, if_match=etag)
                    break
                except ClientError as exc:
                    if not self._is_precondition_error(exc):
                        raise
        self.client.delete_object(Bucket=self.bucket, Key=session_key)

    def _put_session(self, token_hash: str, user_id: str, timestamp: datetime) -> None:
        self._put_json(
            self._session_key(token_hash),
            {
                "token_hash": token_hash,
                "user_id": user_id,
                "created_at": timestamp.isoformat(),
                "expires_at": (timestamp + timedelta(days=SESSION_DAYS)).isoformat(),
            },
            if_none_match=True,
        )

    def _list_sync(
        self,
        user_id: str,
        limit: int,
        offset: int,
        sort: str,
        query: str,
    ) -> HistoryListResponse:
        query = query.strip().casefold()
        items = []
        for key in self._list_keys(self._key(f"packs/{user_id}/")):
            pack, _ = self._get_json(key)
            if pack is None or (
                query and query not in pack["request"]["motion"].casefold()
            ):
                continue
            items.append(self._history_item(pack))
        items.sort(key=lambda item: item.updated_at, reverse=sort != "asc")
        return HistoryListResponse(
            items=items[offset : offset + limit],
            total=len(items),
            retention_days=self.retention_days,
        )

    def _get_sync(self, user_id: str, generation_id: str) -> Optional[PackDetail]:
        pack, _ = self._get_json(self._pack_key(user_id, generation_id))
        if pack is None:
            return None
        return self._pack_detail(pack)

    def _delete_sync(self, user_id: str, generation_id: str) -> bool:
        key = self._pack_key(user_id, generation_id)
        pack, _ = self._get_json(key)
        if pack is None:
            return False
        self.client.delete_object(Bucket=self.bucket, Key=key)
        return True

    def _update_pack_sync(
        self,
        user_id: str,
        generation_id: str,
        mutator: Callable[[dict[str, Any]], None],
    ) -> bool:
        key = self._pack_key(user_id, generation_id)
        for _ in range(4):
            pack, etag = self._get_json(key)
            if pack is None:
                return False
            mutator(pack)
            try:
                self._put_json(key, pack, if_match=etag)
                return True
            except ClientError as exc:
                if not self._is_precondition_error(exc):
                    raise
        raise RuntimeError("Could not update the debate pack safely.")

    def _cleanup_sync(self, timestamp: datetime) -> int:
        cutoff = timestamp - timedelta(days=self.retention_days)
        expired_pack_keys = []
        active_user_ids = set()
        for key in self._list_keys(self._key("packs/")):
            pack, _ = self._get_json(key)
            if pack is None:
                continue
            if datetime.fromisoformat(pack["updated_at"]) <= cutoff:
                expired_pack_keys.append(key)
            else:
                active_user_ids.add(pack["user_id"])
        self._delete_keys(expired_pack_keys)

        active_session_users = set()
        expired_session_keys = []
        for key in self._list_keys(self._key("sessions/")):
            session, _ = self._get_json(key)
            if session is None:
                continue
            if datetime.fromisoformat(session["expires_at"]) <= timestamp:
                expired_session_keys.append(key)
            else:
                active_session_users.add(session["user_id"])
        self._delete_keys(expired_session_keys)

        for key in self._list_keys(self._key("users/")):
            user, _ = self._get_json(key)
            if (
                user
                and user.get("is_guest")
                and user["user_id"] not in active_user_ids
                and user["user_id"] not in active_session_users
            ):
                self.client.delete_object(Bucket=self.bucket, Key=key)
        return len(expired_pack_keys)

    def _history_item(self, pack: dict[str, Any]) -> HistoryItem:
        request = pack["request"]
        updated_at = datetime.fromisoformat(pack["updated_at"])
        return HistoryItem(
            generation_id=pack["generation_id"],
            motion=request["motion"],
            side=request["side"],
            speaker_roles=request["speaker_roles"],
            language=request["language"],
            research_depth=request["research_depth"],
            created_at=datetime.fromisoformat(pack["created_at"]),
            updated_at=updated_at,
            expires_at=updated_at + timedelta(days=self.retention_days),
        )

    def _pack_detail(self, pack: dict[str, Any]) -> PackDetail:
        updated_at = datetime.fromisoformat(pack["updated_at"])
        response = GenerateResponse.model_validate(pack["latest"])
        response.generation_id = pack["generation_id"]
        return PackDetail(
            generation_id=pack["generation_id"],
            request=GenerateRequest.model_validate(pack["request"]),
            latest=response,
            created_at=datetime.fromisoformat(pack["created_at"]),
            updated_at=updated_at,
            expires_at=updated_at + timedelta(days=self.retention_days),
            versions=[
                PackVersion.model_validate(
                    {key: item[key] for key in ("version_id", "name", "created_at")}
                )
                for item in pack.get("versions", [])
            ],
            messages=[
                PackMessage.model_validate(item) for item in pack.get("messages", [])
            ],
        )

    def _get_json(self, key: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if self._error_status(exc) == 404 or self._error_code(exc) in {
                "NoSuchKey",
                "NoSuchObject",
            }:
                return None, None
            raise
        body = response["Body"].read()
        return json.loads(body.decode("utf-8")), response.get("ETag", "").strip('"')

    def _put_json(
        self,
        key: str,
        payload: dict[str, Any],
        if_match: Optional[str] = None,
        if_none_match: bool = False,
    ) -> None:
        arguments = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8"),
            "ContentType": "application/json",
            "ACL": "private",
        }
        if if_match:
            arguments["IfMatch"] = if_match
        if if_none_match:
            arguments["IfNoneMatch"] = "*"
        self.client.put_object(**arguments)

    def _list_keys(self, prefix: str) -> list[str]:
        keys = []
        token = None
        while True:
            arguments = {
                "Bucket": self.bucket,
                "Prefix": prefix,
                "MaxKeys": 1000,
            }
            if token:
                arguments["ContinuationToken"] = token
            response = self.client.list_objects_v2(**arguments)
            keys.extend(item["Key"] for item in response.get("Contents", []))
            if not response.get("IsTruncated"):
                return keys
            token = response["NextContinuationToken"]

    def _delete_keys(self, keys: list[str]) -> None:
        for start in range(0, len(keys), 1000):
            batch = keys[start : start + 1000]
            if batch:
                self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={
                        "Objects": [{"Key": key} for key in batch],
                        "Quiet": True,
                    },
                )

    def _key(self, suffix: str) -> str:
        return f"{self.prefix}/{suffix.lstrip('/')}"

    def _user_key(self, user_id: str) -> str:
        return self._key(f"users/{user_id}.json")

    def _session_key(self, token_hash: str) -> str:
        return self._key(f"sessions/{token_hash}.json")

    def _username_key(self, username: str) -> str:
        digest = hashlib.sha256(username.casefold().encode("utf-8")).hexdigest()
        return self._key(f"usernames/{digest}.json")

    def _pack_key(self, user_id: str, generation_id: str) -> str:
        return self._key(f"packs/{user_id}/{generation_id}.json")

    @staticmethod
    def _profile(user: dict[str, Any]) -> UserProfile:
        return UserProfile(
            user_id=user["user_id"],
            username=user.get("username"),
            nickname=user["nickname"],
            is_guest=bool(user["is_guest"]),
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

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _s3_endpoint(endpoint: str) -> str:
        parts = urlsplit(endpoint.strip().strip("`"))
        hostname = parts.hostname or ""
        if hostname.startswith("tos-") and not hostname.startswith("tos-s3-"):
            hostname = hostname.replace("tos-", "tos-s3-", 1)
        if parts.port:
            hostname = f"{hostname}:{parts.port}"
        return urlunsplit(
            (parts.scheme or "https", hostname, parts.path, parts.query, parts.fragment)
        ).rstrip("/")

    @staticmethod
    def _error_status(exc: ClientError) -> int:
        return int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))

    @staticmethod
    def _error_code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))

    @classmethod
    def _is_precondition_error(cls, exc: ClientError) -> bool:
        return cls._error_status(exc) in {409, 412} or cls._error_code(exc) in {
            "ConditionalRequestConflict",
            "PreconditionFailed",
        }
