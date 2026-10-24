"""Immutable live sessions and summary events; no transcript/audio columns or TTL."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from app.live_models import LiveRecord, LiveSession
from app.tos_repository import TosGenerationRepository


class LiveRepository:
    def __init__(self, repository):
        self.repository = repository
        self.tos = isinstance(repository, TosGenerationRepository)

    async def initialize(self):
        if not self.tos:
            return  # Tables are migrated with the main SQLite repository.
        rules = await asyncio.to_thread(
            self.repository.client.get_bucket_lifecycle_configuration,
            Bucket=self.repository.bucket,
        )
        live_prefix = self.repository._key("live/")
        for rule in rules.get("Rules", []):
            if rule.get("Status") != "Enabled" or not rule.get("Expiration"):
                continue
            filter_ = rule.get("Filter", {})
            prefix = rule.get("Prefix", filter_.get("Prefix", filter_.get("And", {}).get("Prefix", "")))
            if live_prefix.startswith(prefix) or prefix.startswith(live_prefix):
                raise RuntimeError("TOS lifecycle expiration overlaps permanent live records.")

    def _key(self, user_id, session_id, suffix):
        return self.repository._key(f"live/{user_id}/{session_id}/{suffix}")

    async def create(self, user_id, session):
        payload = session.model_dump(mode="json")
        if self.tos:
            await asyncio.to_thread(
                self.repository._put_json,
                self._key(user_id, session.session_id, "session.json"),
                payload, None, True,
            )
        else:
            def save():
                with self.repository._connect() as conn:
                    conn.execute(
                        "INSERT INTO live_sessions (session_id,user_id,created_at,payload_json) VALUES (?,?,?,?)",
                        (session.session_id, user_id, session.created_at.isoformat(), json.dumps(payload, ensure_ascii=False)),
                    )
            await asyncio.to_thread(save)

    async def get(self, user_id, session_id):
        if self.tos:
            payload, _ = await asyncio.to_thread(
                self.repository._get_json, self._key(user_id, session_id, "session.json")
            )
        else:
            def read():
                with self.repository._connect() as conn:
                    row = conn.execute(
                        "SELECT payload_json FROM live_sessions WHERE user_id=? AND session_id=?",
                        (user_id, session_id),
                    ).fetchone()
                    return json.loads(row[0]) if row else None
            payload = await asyncio.to_thread(read)
        return LiveSession.model_validate(payload) if payload else None

    async def list(self, user_id, limit=30, offset=0):
        def read():
            if self.tos:
                keys = self.repository._list_keys(self.repository._key(f"live/{user_id}/"))
                payloads = [
                    self.repository._get_json(key)[0]
                    for key in keys if key.endswith("/session.json")
                ]
                payloads = sorted((p for p in payloads if p), key=lambda p: p["created_at"], reverse=True)
                return payloads[offset:offset + limit]
            with self.repository._connect() as conn:
                rows = conn.execute(
                    "SELECT payload_json FROM live_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (user_id, limit, offset),
                )
                return [json.loads(row[0]) for row in rows]
        sessions = await asyncio.to_thread(read)
        return [
            {key: payload[key] for key in ("session_id", "motion", "side", "speaking_round", "created_at")}
            for payload in sessions
        ]

    async def records(self, user_id, session_id, limit=None):
        def read():
            if self.tos:
                # Use object timestamps before fetching bodies. Avoid re-reading an
                # entire match on every turn; include opening claims as anchors.
                objects, token = [], None
                while True:
                    args = {"Bucket": self.repository.bucket,
                            "Prefix": self._key(user_id, session_id, "records/"), "MaxKeys": 1000}
                    if token:
                        args["ContinuationToken"] = token
                    response = self.repository.client.list_objects_v2(**args)
                    objects.extend(response.get("Contents", []))
                    if not response.get("IsTruncated"):
                        break
                    token = response["NextContinuationToken"]
                objects.sort(key=lambda item: str(item.get("LastModified", "")))
                if limit and len(objects) > limit:
                    objects = objects[:6] + objects[-(limit - 6):]
                keys = [item["Key"] for item in objects]
                with ThreadPoolExecutor(max_workers=8) as pool:
                    payloads = list(pool.map(lambda key: self.repository._get_json(key)[0], keys))
                return sorted((p for p in payloads if p), key=lambda p: (p["captured_at"], p["event_id"]))
            with self.repository._connect() as conn:
                if limit:
                    recent = conn.execute(
                        "SELECT payload_json FROM live_records WHERE user_id=? AND session_id=? ORDER BY captured_at DESC,event_id DESC LIMIT ?",
                        (user_id, session_id, limit - 6),
                    ).fetchall()
                    opening = conn.execute(
                        "SELECT payload_json FROM live_records WHERE user_id=? AND session_id=? ORDER BY captured_at,event_id LIMIT 6",
                        (user_id, session_id),
                    ).fetchall()
                    payloads = {p["event_id"]: p for p in (json.loads(row[0]) for row in opening + recent)}
                    return sorted(payloads.values(), key=lambda p: (p["captured_at"], p["event_id"]))
                rows = conn.execute("SELECT payload_json FROM live_records WHERE user_id=? AND session_id=? ORDER BY captured_at,event_id",
                                    (user_id, session_id))
                return [json.loads(row[0]) for row in rows]
        return [LiveRecord.model_validate(p) for p in await asyncio.to_thread(read)]

    async def record(self, user_id, session_id, event_id):
        if self.tos:
            payload, _ = await asyncio.to_thread(
                self.repository._get_json,
                self._key(user_id, session_id, f"records/{event_id}.json"),
            )
        else:
            def read():
                with self.repository._connect() as conn:
                    row = conn.execute(
                        "SELECT payload_json FROM live_records WHERE user_id=? AND session_id=? AND event_id=?",
                        (user_id, session_id, event_id),
                    ).fetchone()
                    return json.loads(row[0]) if row else None
            payload = await asyncio.to_thread(read)
        return LiveRecord.model_validate(payload) if payload else None

    async def append(self, user_id, session_id, record):
        # A unique event key makes retries safe, even across function instances.
        def save():
            payload = record.model_dump(mode="json")
            if self.tos:
                try:
                    self.repository._put_json(
                        self._key(user_id, session_id, f"records/{record.event_id}.json"),
                        payload, if_none_match=True,
                    )
                except Exception as exc:
                    from botocore.exceptions import ClientError
                    if not isinstance(exc, ClientError) or not self.repository._is_precondition_error(exc):
                        raise
            else:
                with self.repository._connect() as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO live_records (event_id,session_id,user_id,captured_at,payload_json) VALUES (?,?,?,?,?)",
                        (record.event_id, session_id, user_id, record.captured_at.isoformat(), json.dumps(payload, ensure_ascii=False)),
                    )
        await asyncio.to_thread(save)
        return await self.record(user_id, session_id, record.event_id)
