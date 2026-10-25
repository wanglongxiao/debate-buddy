from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from app.models import OutputLanguage, Side

Round = Literal["1", "2", "3", "4", "crossfire", "reply"]


class LiveSetup(BaseModel):
    motion: str = Field(min_length=5, max_length=500)
    side: Side
    speaking_round: Round
    language: OutputLanguage = OutputLanguage.chinese
    generation_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @field_validator("motion")
    @classmethod
    def clean_motion(cls, value):
        value = " ".join(value.split())
        if len(value) < 5:
            raise ValueError("请输入至少五个字符的辩题。")
        return value


class LiveSession(LiveSetup):
    session_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prep_context: str = ""


class LiveTurn(BaseModel):
    event_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    speaker_side: Side
    round: Round
    text: str = Field(min_length=1, max_length=6000)
    captured_at: datetime

    @field_validator("captured_at")
    @classmethod
    def utc_timestamp(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value):
        if not value.strip():
            raise ValueError("发言内容不能为空。")
        return value.strip()


class HeardArgument(BaseModel):
    claim: str = Field(default="", max_length=240)
    warrant: str = Field(default="", max_length=240)
    impact: str = Field(default="", max_length=240)
    missing_link: str = Field(default="", max_length=240)


class TurnSummary(BaseModel):
    summary: str = Field(max_length=800)
    key_points: List[str] = Field(default_factory=list, max_length=6)
    evidence: List[str] = Field(default_factory=list, max_length=6)
    uncertainties: List[str] = Field(default_factory=list, max_length=4)
    arguments: List[HeardArgument] = Field(default_factory=list, max_length=2)


class LiveAdvice(BaseModel):
    mode: Literal["continue", "rebut", "question", "opening"] = "opening"
    main_clash: str = Field(default="", max_length=300)
    response_strategy: str = Field(default="", max_length=300)
    weighing: str = Field(default="", max_length=400)
    poi_hint: str = Field(default="", max_length=240)
    key_points: List[str] = Field(default_factory=list, max_length=3)
    flaws: List[str] = Field(default_factory=list, max_length=3)
    ready_to_say: str = Field(max_length=1500)
    next_steps: List[str] = Field(default_factory=list, max_length=5)
    questions: List[str] = Field(default_factory=list, max_length=4)
    cited_record_ids: List[str] = Field(default_factory=list, max_length=8)


class LiveRecord(TurnSummary):
    event_id: str
    speaker_side: Side
    round: Round
    captured_at: datetime
    saved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("captured_at")
    @classmethod
    def utc_timestamp(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class LiveQuestion(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value):
        if not value.strip():
            raise ValueError("问题不能为空。")
        return value.strip()
