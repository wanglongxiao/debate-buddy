from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Side(str, Enum):
    proposition = "Proposition"
    opposition = "Opposition"


class OutputLanguage(str, Enum):
    english = "English"
    chinese = "中文"
    bilingual = "Bilingual"


class ResearchDepth(str, Enum):
    quick = "Quick Prep"
    standard = "Standard Prep"
    deep = "Deep Research"


class SpeakerRole(str, Enum):
    first = "1st Speaker"
    second = "2nd Speaker"
    third = "3rd Speaker"
    fourth = "4th Speaker / Reply Speaker / Summary Speaker"


class GenerateRequest(BaseModel):
    motion: str = Field(min_length=5, max_length=500)
    side: Side
    speech_time_minutes: int = Field(default=4, ge=1, le=10)
    speaker_roles: List[SpeakerRole] = Field(min_length=1, max_length=4)
    language: OutputLanguage = OutputLanguage.english
    research_depth: ResearchDepth = ResearchDepth.standard
    source_urls: List[HttpUrl] = Field(default_factory=list, max_length=10)
    source_material: str = Field(default="", max_length=20000)

    @field_validator("motion")
    @classmethod
    def clean_motion(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("speaker_roles")
    @classmethod
    def unique_roles(cls, value: List[SpeakerRole]) -> List[SpeakerRole]:
        return list(dict.fromkeys(value))

    @field_validator("source_material")
    @classmethod
    def clean_source_material(cls, value: str) -> str:
        return value.strip()


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    published_date: Optional[str] = None
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    source_type: str = "Web source"
    credibility: str = "Needs verification"


class KeyConcept(BaseModel):
    term: str
    simple_explanation: str


class MotionUnderstanding(BaseModel):
    plain_meaning: str
    key_concepts: List[KeyConcept] = Field(default_factory=list)
    main_clash: str
    proposition_burden: str
    opposition_burden: str
    easy_attacks_against_opponent: List[str] = Field(default_factory=list)
    risks_for_our_side: List[str] = Field(default_factory=list)


class DefinitionItem(BaseModel):
    term: str
    possible_definitions: List[str] = Field(default_factory=list)
    recommended_definition: str
    why_it_helps: str
    possible_challenge: str


class MainArgument(BaseModel):
    title: str
    explanation: str
    evidence_direction: str
    practice_line: str


class OverallCaseStrategy(BaseModel):
    one_sentence_stance: str
    main_arguments: List[MainArgument] = Field(default_factory=list)
    strongest_argument: str
    most_vulnerable_argument: str
    emphasize: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)


class AttackDefenseItem(BaseModel):
    opponent_point: str
    our_attack_or_risk: str
    our_response: str
    practice_line: str


class CrossFireQuestion(BaseModel):
    question: str
    purpose: str
    follow_up_if_yes: str
    follow_up_if_no: str
    best_for: str


class CrossFire(BaseModel):
    goals: List[str] = Field(default_factory=list)
    questions: List[CrossFireQuestion] = Field(default_factory=list)
    emphasize: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)


class TeamOutlineItem(BaseModel):
    main_tasks: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)


class TeamOutline(BaseModel):
    first_speaker: TeamOutlineItem
    second_speaker: TeamOutlineItem
    third_speaker: TeamOutlineItem
    fourth_speaker: TeamOutlineItem


class SpeechContent(BaseModel):
    outline: List[str] = Field(default_factory=list)
    speech_text: str


class RoleResearch(BaseModel):
    role: str
    role_tasks: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    detailed_arguments: List[MainArgument] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    possible_attacks: List[str] = Field(default_factory=list)
    responses: List[str] = Field(default_factory=list)
    speech_outline: List[str] = Field(default_factory=list)
    speech_text: str


class EvidenceItem(BaseModel):
    aspect: str = ""
    evidence_id: str
    claim: str
    evidence_summary: str
    source_title: str
    source_url: str
    published_date_or_accessed_at: str
    source_type: str
    credibility: str
    why_it_helps_our_side: str
    simple_practice_line: str
    source_excerpt: str = ""
    context_and_method: str = ""
    limitations: str = ""


class VocabularyItem(BaseModel):
    word: str
    simple_english: str
    chinese: str
    example_sentence: str
    debate_useful: bool


class PracticePlan(BaseModel):
    today: List[str] = Field(default_factory=list)
    tomorrow: List[str] = Field(default_factory=list)
    before_tournament: List[str] = Field(default_factory=list)
    youtube_learning: List[str] = Field(default_factory=list)


class CompactContent(BaseModel):
    summary: str = ""
    motion_understanding: MotionUnderstanding
    definitions: List[DefinitionItem] = Field(default_factory=list)
    overall_case_strategy: OverallCaseStrategy
    attack_defense_map: List[AttackDefenseItem] = Field(default_factory=list)
    cross_fire: CrossFire
    first_speaker_speech: SpeechContent
    evidence_bank: List[EvidenceItem] = Field(default_factory=list)


class StructuredResult(CompactContent):
    motion: str
    side: str
    speech_time_minutes: int
    speaker_roles: List[str]
    language: str
    # Accept historical packs, but never emit removed modules in new responses.
    team_outline: Optional[TeamOutline] = Field(default=None, exclude=True)
    my_role_research: List[RoleResearch] = Field(default_factory=list, exclude=True)
    vocabulary_builder: List[VocabularyItem] = Field(default_factory=list, exclude=True)
    practice_plan: Optional[PracticePlan] = Field(default=None, exclude=True)


PACK_SECTIONS = [
    "summary", "motion_understanding", "definitions", "evidence_bank",
    "overall_case_strategy", "attack_defense_map", "cross_fire", "first_speaker_speech",
]


class PackPatch(BaseModel):
    change_summary: str
    summary: Optional[str] = None
    motion_understanding: Optional[MotionUnderstanding] = None
    definitions: Optional[List[DefinitionItem]] = None
    evidence_bank: Optional[List[EvidenceItem]] = None
    overall_case_strategy: Optional[OverallCaseStrategy] = None
    attack_defense_map: Optional[List[AttackDefenseItem]] = None
    cross_fire: Optional[CrossFire] = None
    first_speaker_speech: Optional[SpeechContent] = None


class ResearchPlan(BaseModel):
    queries: List[str] = Field(min_length=5, max_length=7)


class EvidenceExpansion(BaseModel):
    evidence_bank: List[EvidenceItem] = Field(default_factory=list, max_length=8)


class SpeechExportRequest(BaseModel):
    role: SpeakerRole
    sections: List[str] = Field(min_length=1, max_length=8)
    pack: Optional[StructuredResult] = None

    @field_validator("sections")
    @classmethod
    def valid_sections(cls, value):
        if any(section not in PACK_SECTIONS for section in value):
            raise ValueError("Unknown pack section")
        return list(dict.fromkeys(value))


class DebateSpeech(BaseModel):
    title: str
    role: str
    outline: List[str]
    speech_text: str
    evidence_ids: List[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    generation_id: Optional[str] = None
    structured_result: StructuredResult
    markdown_result: str
    research_warnings: List[str] = Field(default_factory=list)
    changed_sections: List[str] = Field(default_factory=list)
    change_summary: str = ""


class UserProfile(BaseModel):
    user_id: str
    username: Optional[str] = None
    nickname: str
    is_guest: bool


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=50)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("nickname")
    @classmethod
    def clean_nickname(cls, value: str) -> str:
        return " ".join(value.split())


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class ProfileUpdateRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)

    @field_validator("nickname")
    @classmethod
    def clean_nickname(cls, value: str) -> str:
        return " ".join(value.split())


class HistoryItem(BaseModel):
    generation_id: str
    motion: str
    side: str
    speaker_roles: List[str]
    language: str
    research_depth: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class HistoryListResponse(BaseModel):
    items: List[HistoryItem] = Field(default_factory=list)
    total: int
    retention_days: int


class PackVersion(BaseModel):
    version_id: str
    name: str
    created_at: datetime


class PackMessage(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: datetime


class PackDetail(BaseModel):
    generation_id: str
    request: GenerateRequest
    latest: GenerateResponse
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    versions: List[PackVersion] = Field(default_factory=list)
    messages: List[PackMessage] = Field(default_factory=list)


class AgentUpdateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    sections: List[str] = Field(default_factory=list, max_length=8)

    @field_validator("sections")
    @classmethod
    def valid_sections(cls, value):
        if any(section not in PACK_SECTIONS for section in value):
            raise ValueError("Unknown pack section")
        return list(dict.fromkeys(value))

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        return value.strip()


class RulesStatus(BaseModel):
    loaded: bool
    source: str
    character_count: int
    last_loaded_at: Optional[datetime] = None
    warnings: List[str] = Field(default_factory=list)


class LLMJsonResponse(BaseModel):
    data: Dict[str, Any]
