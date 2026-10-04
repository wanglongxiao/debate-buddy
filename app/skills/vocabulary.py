import json

from pydantic import BaseModel, Field

from app.llm_client import ModelArkClient
from app.models import GenerateRequest, VocabularyItem
from app.skills.motion_analyzer import MotionAnalysisResult


class VocabularyResult(BaseModel):
    vocabulary_builder: list[VocabularyItem] = Field(default_factory=list)


class VocabularySkill:
    def __init__(self, llm: ModelArkClient):
        self.llm = llm

    async def run(
        self, request: GenerateRequest, analysis: MotionAnalysisResult
    ) -> list[VocabularyItem]:
        template = self.llm.read_prompt("vocabulary.md")
        prompt = template.format(
            request_json=json.dumps(request.model_dump(mode="json"), ensure_ascii=False),
            analysis_json=analysis.model_dump_json(),
        )
        result = await self.llm.generate_json(
            prompt,
            VocabularyResult,
            temperature=0.2,
            max_tokens=3500,
        )
        return result.vocabulary_builder[:15]
