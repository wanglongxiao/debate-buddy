import json
import logging
import re

from fastapi import HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.live_models import LiveQuestion, LiveSession, LiveSetup, LiveTurn
from app.llm_client import LLMConfigurationError, LLMResponseError
from app.services.live import LiveCoach, transcribe_audio
from app.services.debate_framework import prepared_snapshot

logger = logging.getLogger(__name__)


def install_live_routes(app, settings, require_storage, get_repository):
    coach = LiveCoach(settings)

    def storage(request):
        _, user = require_storage(request)
        repository, ready = get_repository()
        if not ready:
            raise HTTPException(503, "比赛摘要存储暂不可用，请稍后再试。")
        return repository, user

    async def session_for(request, session_id):
        repository, user = storage(request)
        if not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise HTTPException(404, "比赛不存在。")
        session = await repository.get(user.user_id, session_id)
        if session is None:
            raise HTTPException(404, "比赛不存在。")
        return repository, user, session

    def encode(kind, **kwargs):
        return json.dumps({"type": kind, **kwargs}, ensure_ascii=False) + "\n"

    @app.get("/api/live/capabilities")
    async def capabilities(request: Request):
        _, ready = get_repository()
        user = getattr(request.state, "user", None)
        return {
            "asr_configured": settings.asr_ready,
            "asr_provider": settings.effective_asr_provider if settings.asr_ready else None,
            "llm_configured": settings.llm_ready,
            "storage_ready": ready and user is not None,
            "is_guest": user.is_guest if user else True,
            "audio_chunk_seconds": 3,
            "summary_interval_seconds": 10,
            "asr_streaming": settings.asr_ready and settings.effective_asr_provider == "seed",
            "max_audio_bytes": 1_000_000,
        }

    @app.get("/api/live/sessions")
    async def sessions(request: Request, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0)):
        repository, user = storage(request)
        return {"items": await repository.list(user.user_id, limit, offset)}

    @app.post("/api/live/sessions")
    async def create(payload: LiveSetup, request: Request):
        repository, user = storage(request)
        if not settings.llm_ready:
            raise HTTPException(503, "请先配置 ModelArk 文字模型。")
        session = LiveSession(**payload.model_dump())
        if payload.generation_id:
            packs, _ = require_storage(request)
            pack = await packs.get(user.user_id, payload.generation_id)
            if pack is None:
                raise HTTPException(404, "准备包不存在或已过期。")
            session.motion = pack.request.motion
            structured = pack.latest.structured_result
            # Snapshot important material so a pack expiry does not break this match.
            session.prep_context = prepared_snapshot(structured, session.speaking_round)
        await repository.create(user.user_id, session)
        return {"session": session.model_dump(mode="json", exclude={"prep_context"}), "records": []}

    @app.get("/api/live/sessions/{session_id}")
    async def detail(session_id: str, request: Request):
        repository, user, session = await session_for(request, session_id)
        records = await repository.records(user.user_id, session_id)
        return {
            "session": session.model_dump(mode="json", exclude={"prep_context"}),
            "records": [r.model_dump(mode="json") for r in records],
        }

    @app.post("/api/live/sessions/{session_id}/turns")
    async def turn(session_id: str, payload: LiveTurn, request: Request):
        repository, user, session = await session_for(request, session_id)

        async def stream():
            saved = False
            try:
                yield encode("progress", message="正在提炼观点与证据…")
                record = await repository.record(user.user_id, session_id, payload.event_id)
                if record is None:
                    summary = await coach.summarize(session, payload)
                    record = await repository.append(user.user_id, session_id, summary)
                saved = True
                yield encode("summary", record=record.model_dump(mode="json"))
                yield encode("progress", message="摘要已保存，正在生成回应…")
                records = await repository.records(user.user_id, session_id, limit=40)
                advice = await coach.advise(session, records, source=record)
                yield encode("advice", advice=advice.model_dump(mode="json"), event_id=record.event_id,
                             speaker_side=record.speaker_side.value, round=record.round)
            except (LLMConfigurationError, LLMResponseError):
                yield encode("error", saved=saved, error=(
                    "摘要已保存，建议生成失败。可在下方重新提问。"
                    if saved else "摘要未保存，请重试；待处理文字仍保留在当前页面。"
                ))
            except Exception as exc:
                logger.error("Live turn failed session=%s saved=%s error=%s", session_id, saved, type(exc).__name__)
                yield encode("error", saved=saved, error=(
                    "摘要已保存，但建议暂不可用。" if saved else "摘要存储失败，请重试。"
                ))
            yield encode("done", saved=saved)
        return StreamingResponse(stream(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})

    @app.post("/api/live/sessions/{session_id}/ask")
    async def ask(session_id: str, payload: LiveQuestion, request: Request):
        repository, user, session = await session_for(request, session_id)

        async def stream():
            try:
                yield encode("progress", message="正在结合比赛记录回答…")
                records = await repository.records(user.user_id, session_id)
                advice = await coach.advise(session, records, payload.message)
                yield encode("advice", advice=advice.model_dump(mode="json"))
            except (LLMConfigurationError, LLMResponseError):
                yield encode("error", error="回答暂不可用，请稍后重试。")
            except Exception as exc:
                logger.error("Live question failed session=%s error=%s", session_id, type(exc).__name__)
                yield encode("error", error="比赛记录读取失败，请稍后重试。")
            yield encode("done")
        return StreamingResponse(stream(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})

    async def read_audio(session_id, request):
        await session_for(request, session_id)
        if not settings.asr_ready:
            raise HTTPException(503, "服务器 ASR 尚未配置。")
        audio = bytearray()
        async for chunk in request.stream():
            audio.extend(chunk)
            if len(audio) > 1_000_000:
                raise HTTPException(413, "音频分段过大。")
        if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise HTTPException(400, "请提供 WAV 音频分段。")
        return bytes(audio)

    @app.post("/api/live/sessions/{session_id}/transcribe/stream")
    async def transcribe_stream(session_id: str, request: Request, language: str = Query("zh", pattern="^(zh|en)$")):
        audio = await read_audio(session_id, request)

        async def stream():
            try:
                if settings.effective_asr_provider == "seed":
                    from app.services.seed_speech import stream_seed
                    async for event in stream_seed(settings, audio, language):
                        yield encode(event["type"], text=event["text"])
                else:
                    yield encode("final", text=await transcribe_audio(settings, audio, language))
            except LLMResponseError as exc:
                yield encode("error", error=str(exc))
            yield encode("done")

        return StreamingResponse(stream(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})

    @app.post("/api/live/sessions/{session_id}/transcribe")
    async def transcribe(session_id: str, request: Request, language: str = Query("zh", pattern="^(zh|en)$")):
        audio = await read_audio(session_id, request)
        try:
            return {"text": await transcribe_audio(settings, audio, language)}
        except LLMResponseError as exc:
            raise HTTPException(502, str(exc)) from exc
