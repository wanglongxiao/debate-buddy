import json

from pydantic import BaseModel, Field

from app.llm_client import ModelArkClient
from app.models import DefinitionItem, GenerateRequest, MotionUnderstanding


class MotionAnalysisResult(BaseModel):
    motion_understanding: MotionUnderstanding
    definitions: list[DefinitionItem] = Field(default_factory=list)
    research_queries: list[str] = Field(default_factory=list)


class MotionAnalyzerSkill:
    def __init__(self, llm: ModelArkClient):
        self.llm = llm

    async def run(self, request: GenerateRequest) -> MotionAnalysisResult:
        template = self.llm.read_prompt("motion_analysis.md")
        prompt = template.format(
            request_json=json.dumps(request.model_dump(mode="json"), ensure_ascii=False)
        )
        return await self.llm.generate_json(
            prompt,
            MotionAnalysisResult,
            temperature=0.15,
            max_tokens=3500,
        )
