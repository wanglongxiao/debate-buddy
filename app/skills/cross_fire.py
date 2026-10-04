import json

from app.llm_client import ModelArkClient
from app.models import CrossFire, GenerateRequest
from app.skills.case_builder import CaseBuilderResult
from app.skills.motion_analyzer import MotionAnalysisResult


class CrossFireCoachSkill:
    def __init__(self, llm: ModelArkClient):
        self.llm = llm

    async def run(
        self,
        request: GenerateRequest,
        analysis: MotionAnalysisResult,
        case: CaseBuilderResult,
    ) -> CrossFire:
        template = self.llm.read_prompt("cross_fire.md")
        prompt = template.format(
            request_json=json.dumps(request.model_dump(mode="json"), ensure_ascii=False),
            analysis_json=analysis.model_dump_json(),
            case_json=case.model_dump_json(),
        )
        return await self.llm.generate_json(
            prompt,
            CrossFire,
            temperature=0.25,
            max_tokens=4000,
        )
