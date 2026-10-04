import asyncio

from app.config import Settings
from app.llm_client import ModelArkClient
from app.models import GenerateRequest, GenerateResponse, StructuredResult
from app.services.markdown_exporter import MarkdownExporter
from app.skills import (
    CaseBuilderSkill,
    CrossFireCoachSkill,
    DebateRulesSkill,
    EvidenceEvaluatorSkill,
    MotionAnalyzerSkill,
    SpeechWriterSkill,
    VocabularySkill,
    WebResearchSkill,
)


class DebateGeneratorService:
    def __init__(self, settings: Settings, rules_skill: DebateRulesSkill):
        llm = ModelArkClient(settings)
        self.rules = rules_skill
        self.motion_analyzer = MotionAnalyzerSkill(llm)
        self.web_research = WebResearchSkill(settings)
        self.evidence_evaluator = EvidenceEvaluatorSkill(llm)
        self.case_builder = CaseBuilderSkill(llm)
        self.cross_fire = CrossFireCoachSkill(llm)
        self.speech_writer = SpeechWriterSkill(llm)
        self.vocabulary = VocabularySkill(llm)
        self.markdown = MarkdownExporter()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        analysis_task = asyncio.create_task(self.motion_analyzer.run(request))
        rules_task = asyncio.create_task(self.rules.load())
        analysis, rules_status = await asyncio.gather(analysis_task, rules_task)

        sources, research_warnings = await self.web_research.run(
            request, analysis.research_queries
        )
        evidence = await self.evidence_evaluator.run(request, sources)
        if sources and not evidence:
            research_warnings.append(
                "Search results were found, but no evidence passed structured validation."
            )
        elif evidence and all(
            item.claim.startswith("Source material:") for item in evidence
        ):
            research_warnings.append(
                "The AI evidence evaluator was unavailable. Real source excerpts were "
                "preserved for manual verification."
            )

        case = await self.case_builder.run(
            request,
            analysis,
            evidence,
            self.rules.context_excerpt(),
        )

        cross_fire_task = asyncio.create_task(
            self.cross_fire.run(request, analysis, case)
        )
        speech_task = asyncio.create_task(
            self.speech_writer.run(request, analysis, case, evidence)
        )
        vocabulary_task = asyncio.create_task(self.vocabulary.run(request, analysis))
        cross_fire, speeches, vocabulary = await asyncio.gather(
            cross_fire_task, speech_task, vocabulary_task
        )

        selected_roles = {role.value for role in request.speaker_roles}
        role_research = [
            item for item in speeches.my_role_research if item.role in selected_roles
        ]
        if len(role_research) != len(selected_roles):
            research_warnings.append(
                "The AI did not return every selected speaker role. Try generating again."
            )

        structured = StructuredResult(
            motion=request.motion,
            side=request.side.value,
            speech_time_minutes=request.speech_time_minutes,
            speaker_roles=[role.value for role in request.speaker_roles],
            language=request.language.value,
            motion_understanding=analysis.motion_understanding,
            definitions=analysis.definitions,
            overall_case_strategy=case.overall_case_strategy,
            attack_defense_map=case.attack_defense_map,
            cross_fire=cross_fire,
            team_outline=case.team_outline,
            first_speaker_speech=speeches.first_speaker_speech,
            my_role_research=role_research,
            evidence_bank=evidence,
            vocabulary_builder=vocabulary,
            practice_plan=case.practice_plan,
        )
        markdown = self.markdown.export(structured)
        return GenerateResponse(
            structured_result=structured,
            markdown_result=markdown,
            research_warnings=[*rules_status.warnings, *research_warnings],
        )
