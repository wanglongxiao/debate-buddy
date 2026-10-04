import json

from pydantic import BaseModel, Field

from app.llm_client import ModelArkClient
from app.models import EvidenceItem, GenerateRequest, RoleResearch, SpeechContent
from app.skills.case_builder import CaseBuilderResult
from app.skills.motion_analyzer import MotionAnalysisResult


class SpeechWriterResult(BaseModel):
    first_speaker_speech: SpeechContent
    my_role_research: list[RoleResearch] = Field(default_factory=list)


class SpeechWriterSkill:
    def __init__(self, llm: ModelArkClient):
        self.llm = llm

    async def run(
        self,
        request: GenerateRequest,
        analysis: MotionAnalysisResult,
        case: CaseBuilderResult,
        evidence: list[EvidenceItem],
    ) -> SpeechWriterResult:
        target_words = request.speech_time_minutes * 115
        template = self.llm.read_prompt("speech_writer.md")
        prompt = template.format(
            request_json=json.dumps(request.model_dump(mode="json"), ensure_ascii=False),
            target_words=target_words,
            analysis_json=analysis.model_dump_json(),
            case_json=case.model_dump_json(),
            evidence_json=json.dumps(
                [item.model_dump(mode="json") for item in evidence], ensure_ascii=False
            ),
        )
        return await self.llm.generate_json(
            prompt,
            SpeechWriterResult,
            temperature=0.3,
            max_tokens=8000,
        )
