import asyncio
import logging
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_DIR, get_settings
from app.database import GenerationRepository
from app.llm_client import LLMConfigurationError, LLMResponseError
from app.models import (
    GenerateRequest,
    GenerateResponse,
    HistoryListResponse,
    RulesStatus,
)
from app.services.generator import DebateGeneratorService
from app.skills.debate_rules import DebateRulesSkill


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

rules_skill = DebateRulesSkill(settings)
generator_service = DebateGeneratorService(settings, rules_skill)
generation_repository = GenerationRepository(
    settings.database_path,
    settings.data_retention_days,
) if settings.enable_local_history else None


async def periodic_database_cleanup() -> None:
    if generation_repository is None:
        return
    interval_seconds = settings.database_cleanup_interval_hours * 60 * 60
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            deleted = await generation_repository.cleanup()
            if deleted:
                logger.info("Deleted %s expired generation records", deleted)
        except Exception:
            logger.exception("Scheduled database cleanup failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_task = None
    if generation_repository is not None:
        await generation_repository.initialize()
        deleted = await generation_repository.cleanup()
        logger.info(
            "SQLite temporary storage ready at %s; deleted %s expired records",
            settings.database_path,
            deleted,
        )
        cleanup_task = asyncio.create_task(periodic_database_cleanup())
    else:
        logger.info("Local history storage is disabled")
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


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": settings.app_name},
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
        "database_ready": (
            settings.database_path.exists()
            if generation_repository is not None
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


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    try:
        response = await generator_service.generate(request)
        if generation_repository is not None:
            try:
                await generation_repository.save(request, response)
            except Exception:
                logger.exception("Could not save generated debate pack to SQLite")
        return response
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Debate pack generation failed")
        raise HTTPException(
            status_code=500,
            detail="Generation failed. Please check the server logs and try again.",
        ) from exc


@app.get("/api/history", response_model=HistoryListResponse)
async def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> HistoryListResponse:
    if generation_repository is None:
        raise HTTPException(
            status_code=503,
            detail="History is disabled in this stateless deployment.",
        )
    return await generation_repository.list(limit=limit, offset=offset)


@app.get("/api/history/{generation_id}", response_model=GenerateResponse)
async def get_history(generation_id: str) -> GenerateResponse:
    if generation_repository is None:
        raise HTTPException(
            status_code=503,
            detail="History is disabled in this stateless deployment.",
        )
    response = await generation_repository.get(generation_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Generation not found or expired.")
    return response


@app.delete("/api/history/{generation_id}")
async def delete_history(generation_id: str) -> dict[str, bool]:
    if generation_repository is None:
        raise HTTPException(
            status_code=503,
            detail="History is disabled in this stateless deployment.",
        )
    deleted = await generation_repository.delete(generation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Generation not found or expired.")
    return {"deleted": True}
