import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_DIR, get_settings
from app.database import (
    GenerationRepository,
    InvalidCredentialsError,
    UsernameExistsError,
)
from app.llm_client import LLMConfigurationError, LLMResponseError
from app.models import (
    AgentUpdateRequest,
    GenerateRequest,
    GenerateResponse,
    HistoryListResponse,
    LoginRequest,
    PackDetail,
    PackVersion,
    ProfileUpdateRequest,
    RegisterRequest,
    RulesStatus,
    UserProfile,
)
from app.services.generator import DebateGeneratorService
from app.skills.debate_rules import DebateRulesSkill
from app.tos_repository import TosGenerationRepository

SESSION_COOKIE = "debate_buddy_session"
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

rules_skill = DebateRulesSkill(settings)
generator_service = DebateGeneratorService(settings, rules_skill)


def build_generation_repository():
    if settings.storage_backend == "tos":
        if not settings.tos_ready:
            raise RuntimeError(
                "TOS storage requires BYTEPLUS_AK, BYTEPLUS_SK, TOS_BUCKET, "
                "TOS_ENDPOINT, and TOS_REGION."
            )
        return TosGenerationRepository(
            access_key=settings.byteplus_ak,
            secret_key=settings.byteplus_sk,
            endpoint=settings.tos_endpoint,
            region=settings.tos_region,
            bucket=settings.tos_bucket,
            prefix=settings.tos_prefix,
            retention_days=settings.data_retention_days,
        )
    if settings.storage_backend == "disabled" or not settings.enable_local_history:
        return None
    return GenerationRepository(settings.database_path, settings.data_retention_days)


generation_repository = build_generation_repository()


async def periodic_storage_cleanup() -> None:
    if generation_repository is None:
        return
    interval_seconds = settings.database_cleanup_interval_hours * 60 * 60
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            deleted = await generation_repository.cleanup()
            if deleted:
                logger.info("Deleted %s expired debate packs", deleted)
        except Exception:
            logger.exception("Scheduled storage cleanup failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_task = None
    if generation_repository is not None:
        await generation_repository.initialize()
        deleted = await generation_repository.cleanup()
        logger.info(
            "%s storage ready; deleted %s expired packs",
            settings.storage_backend.upper(),
            deleted,
        )
        cleanup_task = asyncio.create_task(periodic_storage_cleanup())
    else:
        logger.info("Profile and history storage is disabled")
    try:
        status = await rules_skill.load()
        logger.info(
            "Debate rules loaded from %s (%s characters)",
            status.source,
            status.character_count,
        )
    except Exception as exc:
        logger.warning("Initial debate rules load failed: %s", type(exc).__name__)
    try:
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.middleware("http")
async def user_session(request: Request, call_next):
    if generation_repository is not None and not request.url.path.startswith(
        "/static/"
    ):
        token = request.cookies.get(SESSION_COOKIE, "")
        profile = await generation_repository.resolve_session(token)
        if profile is None:
            profile, token = await generation_repository.create_guest_session()
        request.state.user = profile
        request.state.session_token = token
    response = await call_next(request)
    token = getattr(request.state, "session_token", None)
    if token and token != request.cookies.get(SESSION_COOKIE):
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=360 * 24 * 60 * 60,
            httponly=True,
            secure=settings.app_env == "production",
            samesite="lax",
        )
    return response


def require_history(request: Request):
    if generation_repository is None:
        raise HTTPException(
            status_code=503,
            detail="Profiles and history are disabled in this deployment.",
        )
    return generation_repository, request.state.user


def progress_stream(
    runner: Callable[
        [Callable[[str, int, str, Optional[List[Dict[str, str]]]], None]],
        Awaitable[Any],
    ],
) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()

    def progress(
        step: str,
        percent: int,
        message: str = "",
        resources: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        queue.put_nowait(
            {
                "type": "progress",
                "step": step,
                "progress": percent,
                "message": message,
                "resources": resources or [],
            }
        )

    async def execute() -> None:
        try:
            result = await runner(progress)
            if hasattr(result, "model_dump"):
                result = result.model_dump(mode="json")
            await queue.put({"type": "result", "result": result})
        except asyncio.CancelledError:
            logger.info("Streaming generation was cancelled by the client")
            raise
        except (LLMConfigurationError, LLMResponseError) as exc:
            await queue.put({"type": "error", "error": str(exc)})
        except Exception:
            logger.exception("Streaming generation failed")
            await queue.put(
                {
                    "type": "error",
                    "error": "Generation failed. Check the server logs and try again.",
                }
            )
        finally:
            await queue.put(None)

    async def stream():
        worker = asyncio.create_task(execute())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield json.dumps(event, ensure_ascii=False) + "\n"
        finally:
            if not worker.done():
                worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "webpage_timeout_seconds": settings.webpage_timeout_seconds,
        },
    )


@app.get("/api/health")
async def health() -> dict[str, object]:
    stored_generations = (
        await generation_repository.count()
        if generation_repository is not None
        else None
    )
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_configured": settings.llm_ready,
        "rules_loaded": rules_skill.status.loaded,
        "history_enabled": generation_repository is not None,
        "storage_backend": (
            settings.storage_backend
            if generation_repository is not None
            else "disabled"
        ),
        "database_ready": (
            settings.database_path.exists()
            if generation_repository is not None
            and settings.storage_backend == "sqlite"
            else False
        ),
        "stored_generations": stored_generations,
        "data_retention_days": settings.data_retention_days,
    }


@app.get("/api/rules/status", response_model=RulesStatus)
async def rules_status() -> RulesStatus:
    if not rules_skill.status.loaded:
        await rules_skill.load()
    return rules_skill.status


@app.post("/api/rules/refresh", response_model=RulesStatus)
async def refresh_rules() -> RulesStatus:
    return await rules_skill.load(force_refresh=True)


@app.get("/api/auth/me", response_model=UserProfile)
async def get_profile(request: Request) -> UserProfile:
    _, user = require_history(request)
    return user


@app.post("/api/auth/register", response_model=UserProfile)
async def register(payload: RegisterRequest, request: Request) -> UserProfile:
    repository, user = require_history(request)
    try:
        profile, token = await repository.register(
            user.user_id,
            payload.username,
            payload.password,
            payload.nickname,
        )
    except UsernameExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    request.state.user = profile
    request.state.session_token = token
    return profile


@app.post("/api/auth/login", response_model=UserProfile)
async def login(payload: LoginRequest, request: Request) -> UserProfile:
    repository, _ = require_history(request)
    try:
        profile, token = await repository.login(payload.username, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    request.state.user = profile
    request.state.session_token = token
    return profile


@app.post("/api/auth/logout", response_model=UserProfile)
async def logout(request: Request) -> UserProfile:
    repository, _ = require_history(request)
    old_token = request.cookies.get(SESSION_COOKIE, "")
    if old_token:
        await repository.revoke_session(old_token)
    profile, token = await repository.create_guest_session()
    request.state.user = profile
    request.state.session_token = token
    return profile


@app.patch("/api/profile", response_model=UserProfile)
async def update_profile(
    payload: ProfileUpdateRequest, request: Request
) -> UserProfile:
    repository, user = require_history(request)
    profile = await repository.update_profile(user.user_id, payload.nickname)
    request.state.user = profile
    return profile


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest, request: Request) -> GenerateResponse:
    try:
        response = await generator_service.generate(payload)
        if generation_repository is not None:
            try:
                user = request.state.user
                await generation_repository.save(user.user_id, payload, response)
            except Exception:
                logger.exception("Could not save generated debate pack")
        return response
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Debate pack generation failed")
        raise HTTPException(
            status_code=500,
            detail="Generation failed. Check the server logs and try again.",
        ) from exc


@app.post("/api/generate/stream")
async def generate_stream(
    payload: GenerateRequest, request: Request
) -> StreamingResponse:
    user = getattr(request.state, "user", None)

    async def run(progress):
        response = await generator_service.generate(payload, progress)
        if generation_repository is not None and user is not None:
            await generation_repository.save(user.user_id, payload, response)
        return response

    return progress_stream(run)


@app.get("/api/history", response_model=HistoryListResponse)
async def list_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
    q: str = Query(default="", max_length=200),
) -> HistoryListResponse:
    repository, user = require_history(request)
    return await repository.list(
        user.user_id, limit=limit, offset=offset, sort=sort, query=q
    )


@app.get("/api/history/{generation_id}", response_model=PackDetail)
async def get_history(generation_id: str, request: Request) -> PackDetail:
    repository, user = require_history(request)
    pack = await repository.get(user.user_id, generation_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Debate pack not found or expired.")
    return pack


@app.delete("/api/history/{generation_id}")
async def delete_history(generation_id: str, request: Request) -> dict[str, bool]:
    repository, user = require_history(request)
    deleted = await repository.delete(user.user_id, generation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Debate pack not found or expired.")
    return {"deleted": True}


@app.post(
    "/api/history/{generation_id}/agent",
    response_model=PackDetail,
)
async def update_history_with_agent(
    generation_id: str,
    payload: AgentUpdateRequest,
    request: Request,
) -> PackDetail:
    repository, user = require_history(request)
    pack = await repository.get(user.user_id, generation_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Debate pack not found or expired.")
    try:
        latest = await generator_service.update_pack(pack, payload.message)
        updated = await repository.update_latest(
            user.user_id, generation_id, latest, payload.message
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Debate pack not found.")
        result = await repository.get(user.user_id, generation_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Debate pack not found.")
        return result
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/history/{generation_id}/agent/stream")
async def update_history_with_agent_stream(
    generation_id: str,
    payload: AgentUpdateRequest,
    request: Request,
) -> StreamingResponse:
    repository, user = require_history(request)
    pack = await repository.get(user.user_id, generation_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Debate pack not found or expired.")

    async def run(progress):
        latest = await generator_service.update_pack(pack, payload.message, progress)
        updated = await repository.update_latest(
            user.user_id, generation_id, latest, payload.message
        )
        if not updated:
            raise RuntimeError("Debate pack no longer exists.")
        result = await repository.get(user.user_id, generation_id)
        if result is None:
            raise RuntimeError("Debate pack no longer exists.")
        return result

    return progress_stream(run)


@app.post(
    "/api/history/{generation_id}/versions",
    response_model=PackVersion,
)
async def save_history_version(generation_id: str, request: Request) -> PackVersion:
    repository, user = require_history(request)
    version = await repository.save_version(user.user_id, generation_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Debate pack not found or expired.")
    return version


@app.post(
    "/api/history/{generation_id}/versions/{version_id}/restore",
    response_model=PackDetail,
)
async def restore_history_version(
    generation_id: str, version_id: str, request: Request
) -> PackDetail:
    repository, user = require_history(request)
    pack = await repository.restore_version(user.user_id, generation_id, version_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    return pack
