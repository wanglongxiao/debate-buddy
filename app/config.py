from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = ROOT_DIR / "app"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Debate Buddy"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    modelark_api_key: Optional[str] = Field(default=None)
    modelark_base_url: str = "https://ark.ap-southeast.bytepluses.com/api/v3"
    main_agent_endpoint: Optional[str] = Field(default=None)
    llm_timeout_seconds: float = 900.0
    llm_thinking_mode: Literal["enabled", "disabled"] = "enabled"
    llm_reasoning_effort: Literal["low", "medium", "high"] = "low"
    llm_max_tokens: int = Field(default=120000, ge=1, le=131072)
    webpage_timeout_seconds: int = Field(default=900, ge=1)
    live_llm_timeout_seconds: float = Field(default=45, ge=5, le=120)
    asr_provider: Literal["auto", "seed", "openai"] = "auto"
    speech_appid: Optional[str] = None
    speech_api_key: Optional[str] = None
    speech_asr_url: str = "wss://voice.ap-southeast-1.bytepluses.com/api/v3/sauc/bigmodel_nostream"
    speech_resource_id: str = "volc.seedasr.sauc.duration"
    # Full OpenAI-compatible /audio/transcriptions URL, separate from the text LLM.
    asr_url: Optional[str] = None
    asr_api_key: Optional[str] = None
    asr_model: str = "gpt-4o-mini-transcribe"
    asr_timeout_seconds: float = Field(default=20, ge=1, le=60)

    search_provider: Literal[
        "auto", "tavily", "serper", "brave", "google", "openalex", "duckduckgo"
    ] = "auto"
    tavily_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    brave_search_api_key: Optional[str] = None
    google_chrome_path: Optional[str] = None
    search_timeout_seconds: float = 15.0
    search_results_per_query: int = Field(default=4, ge=1, le=10)

    rules_cache_hours: int = Field(default=24, ge=1)
    rules_cache_path: Path = APP_DIR / "data" / "cache" / "debate_rules.json"
    storage_backend: Literal["sqlite", "tos", "disabled"] = "sqlite"
    enable_local_history: bool = True
    database_path: Path = APP_DIR / "data" / "debate_buddy.db"
    data_retention_days: int = Field(default=360, ge=1)
    database_cleanup_interval_hours: int = Field(default=24, ge=1)
    byteplus_ak: Optional[str] = None
    byteplus_sk: Optional[str] = None
    tos_region: str = "ap-southeast-1"
    tos_bucket: Optional[str] = None
    tos_endpoint: str = "https://tos-ap-southeast-1.bytepluses.com"
    tos_prefix: str = "debate-buddy/v1"

    @property
    def llm_ready(self) -> bool:
        return bool(self.modelark_api_key and self.main_agent_endpoint)

    @property
    def asr_ready(self) -> bool:
        if self.effective_asr_provider == "seed":
            return bool(self.speech_api_key and self.speech_asr_url)
        return bool(self.asr_url and self.asr_api_key)

    @property
    def effective_asr_provider(self) -> str:
        if self.asr_provider == "auto":
            return "seed" if self.speech_api_key else "openai"
        return self.asr_provider

    @property
    def tos_ready(self) -> bool:
        return bool(
            self.byteplus_ak
            and self.byteplus_sk
            and self.tos_bucket
            and self.tos_endpoint
            and self.tos_region
        )

    @property
    def prompts_dir(self) -> Path:
        return APP_DIR / "prompts"

    @property
    def rules_notes_path(self) -> Path:
        return APP_DIR / "data" / "rules_notes.md"


@lru_cache
def get_settings() -> Settings:
    return Settings()
