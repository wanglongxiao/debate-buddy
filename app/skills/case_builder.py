import json

from pydantic import BaseModel, Field

from app.llm_client import ModelArkClient
from app.models import (
    AttackDefenseItem,
    EvidenceItem,
    GenerateRequest,
    OverallCaseStrategy,
    PracticePlan,
    TeamOutline,
)
from app.skills.motion_analyzer import MotionAnalysisResult


class CaseBuilderResult(BaseModel):
    overall_case_strategy: OverallCaseStrategy
    attack_defense_map: list[AttackDefenseItem] = Field(default_factory=list)
    team_outline: TeamOutline
    practice_plan: PracticePlan


class CaseBuilderSkill:
    def __init__(self, llm: ModelArkClient):
        self.llm = llm

    async def run(
        self,
        request: GenerateRequest,
        analysis: MotionAnalysisResult,
        evidence: list[EvidenceItem],
        rules_context: str,
    ) -> CaseBuilderResult:
        template = self.llm.read_prompt("case_builder.md")
        prompt = template.format(
            request_json=json.dumps(request.model_dump(mode="json"), ensure_ascii=False),
            analysis_json=analysis.model_dump_json(),
            evidence_json=json.dumps(
                [item.model_dump(mode="json") for item in evidence], ensure_ascii=False
            ),
            rules_context=rules_context,
        )
        return await self.llm.generate_json(
            prompt,
            CaseBuilderResult,
            temperature=0.25,
            max_tokens=6000,
        )
