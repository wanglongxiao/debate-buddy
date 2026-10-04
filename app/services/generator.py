import asyncio
import json
from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from app.config import Settings
from app.llm_client import ModelArkClient
from app.models import GenerateRequest, GenerateResponse, PackDetail, StructuredResult
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

ProgressCallback = Callable[
    [str, int, str, Optional[List[Dict[str, str]]]],
    None,
]


class DebateGeneratorService:
    def __init__(self, settings: Settings, rules_skill: DebateRulesSkill):
        llm = ModelArkClient(settings)
        self.llm = llm
        self.rules = rules_skill
        self.motion_analyzer = MotionAnalyzerSkill(llm)
        self.web_research = WebResearchSkill(settings)
        self.evidence_evaluator = EvidenceEvaluatorSkill(llm)
        self.case_builder = CaseBuilderSkill(llm)
        self.cross_fire = CrossFireCoachSkill(llm)
        self.speech_writer = SpeechWriterSkill(llm)
        self.vocabulary = VocabularySkill(llm)
        self.markdown = MarkdownExporter()

    async def generate(
        self,
        request: GenerateRequest,
        progress: Optional[ProgressCallback] = None,
    ) -> GenerateResponse:
        self._report(progress, "understanding_motion", 5)
        analysis_task = asyncio.create_task(self.motion_analyzer.run(request))
        rules_task = asyncio.create_task(self.rules.load())
        analysis, rules_status = await self._with_heartbeats(
            asyncio.gather(analysis_task, rules_task),
            progress,
            [
                ("analyzing_clash", 10),
                ("planning_research", 14),
            ],
        )

        self._report(progress, "researching_sources", 18)
        sources, research_warnings = await self._with_heartbeats(
            self.web_research.run(request, analysis.research_queries),
            progress,
            [
                ("querying_web_sources", 24),
                ("querying_academic_sources", 30),
                ("opening_source_pages", 35),
            ],
        )
        resources = [
            {
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type,
            }
            for source in sources
        ]
        self._report(
            progress,
            "sources_collected",
            40,
            f"Collected {len(sources)} sources.",
            resources,
        )
        self._report(progress, "evaluating_evidence", 45, resources=resources)
        evidence = await self._with_heartbeats(
            self.evidence_evaluator.run(request, sources),
            progress,
            [
                ("reasoning_about_evidence", 50),
                ("checking_source_claims", 55),
            ],
            resources,
        )
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

        self._report(progress, "building_case", 60, resources=resources)
        case = await self._with_heartbeats(
            self.case_builder.run(
                request,
                analysis,
                evidence,
                self.rules.context_excerpt(),
            ),
            progress,
            [
                ("reasoning_about_strategy", 64),
                ("drafting_arguments", 68),
                ("checking_case_consistency", 72),
            ],
            resources,
        )

        self._report(progress, "writing_pack", 75, resources=resources)
        cross_fire_task = asyncio.create_task(
            self._tracked_stage(
                self._with_heartbeats(
                    self.cross_fire.run(request, analysis, case),
                    progress,
                    [("reasoning_about_cross_fire", 79)],
                    resources,
                ),
                progress,
                "cross_fire_ready",
                84,
                resources,
            )
        )
        speech_task = asyncio.create_task(
            self._tracked_stage(
                self._with_heartbeats(
                    self.speech_writer.run(request, analysis, case, evidence),
                    progress,
                    [
                        ("planning_speeches", 80),
                        ("drafting_speeches", 86),
                        ("reviewing_speeches", 91),
                    ],
                    resources,
                ),
                progress,
                "speeches_ready",
                94,
                resources,
            )
        )
        vocabulary_task = asyncio.create_task(
            self._tracked_stage(
                self._with_heartbeats(
                    self.vocabulary.run(request, analysis),
                    progress,
                    [("building_vocabulary", 78)],
                    resources,
                ),
                progress,
                "vocabulary_ready",
                88,
                resources,
            )
        )
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
        self._report(progress, "finalizing_pack", 97, resources=resources)
        markdown = self.markdown.export(structured)
        return GenerateResponse(
            structured_result=structured,
            markdown_result=markdown,
            research_warnings=[*rules_status.warnings, *research_warnings],
        )

    async def update_pack(
        self,
        pack: PackDetail,
        message: str,
        progress: Optional[ProgressCallback] = None,
    ) -> GenerateResponse:
        self._report(progress, "reading_pack", 5)
        self._report(progress, "loading_new_sources", 15)
        new_sources, source_warnings = await self.web_research.fetch_user_urls(
            message
        )
        resources = [
            {
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type,
            }
            for source in new_sources
        ]
        self._report(
            progress,
            "updating_pack",
            30,
            f"Loaded {len(new_sources)} new sources.",
            resources,
        )
        template = self.llm.read_prompt("pack_update.md")
        conversation = [
            {"role": item.role, "content": item.content}
            for item in pack.messages
        ]
        conversation.append({"role": "user", "content": message})
        prompt = template.format(
            request_json=json.dumps(
                pack.request.model_dump(mode="json"), ensure_ascii=False
            ),
            current_pack_json=json.dumps(
                pack.latest.structured_result.model_dump(mode="json"),
                ensure_ascii=False,
            ),
            conversation_json=json.dumps(conversation, ensure_ascii=False),
            new_sources_json=json.dumps(
                [
                    {
                        **source.model_dump(mode="json"),
                        "snippet": source.snippet[:2000],
                    }
                    for source in new_sources
                ],
                ensure_ascii=False,
            ),
        )
        structured = await self._with_heartbeats(
            self.llm.generate_json(
                prompt,
                StructuredResult,
                temperature=0.2,
                max_tokens=12000,
            ),
            progress,
            [
                ("model_reading_context", 38),
                ("model_reasoning_request", 46),
                ("model_reworking_strategy", 54),
                ("model_updating_evidence", 62),
                ("model_rewriting_speeches", 70),
                ("model_checking_consistency", 78),
                ("model_final_review", 86),
            ],
            resources,
        )
        self._report(progress, "validating_update", 90, resources=resources)
        existing_sources = {
            item.source_url.rstrip("/"): item
            for item in pack.latest.structured_result.evidence_bank
        }
        fetched_sources = {
            item.url.rstrip("/"): item for item in new_sources
        }
        verified_evidence = []
        for item in structured.evidence_bank:
            normalized_url = item.source_url.rstrip("/")
            existing = existing_sources.get(normalized_url)
            fetched = fetched_sources.get(normalized_url)
            if existing:
                item.source_title = existing.source_title
                item.source_type = existing.source_type
                item.credibility = existing.credibility
                item.published_date_or_accessed_at = (
                    existing.published_date_or_accessed_at
                )
            elif fetched:
                item.source_title = fetched.title
                item.source_type = fetched.source_type
                item.credibility = fetched.credibility
                item.published_date_or_accessed_at = (
                    fetched.published_date or fetched.accessed_at.isoformat()
                )
            else:
                continue
            verified_evidence.append(item)
        structured.evidence_bank = verified_evidence
        self._report(progress, "finalizing_pack", 97, resources=resources)
        return GenerateResponse(
            generation_id=pack.generation_id,
            structured_result=structured,
            markdown_result=self.markdown.export(structured),
            research_warnings=[
                *pack.latest.research_warnings,
                *source_warnings,
            ],
        )

    @staticmethod
    def _report(
        progress: Optional[ProgressCallback],
        step: str,
        percent: int,
        message: str = "",
        resources: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        if progress:
            progress(step, percent, message, resources)

    async def _tracked_stage(
        self,
        coroutine,
        progress: Optional[ProgressCallback],
        step: str,
        percent: int,
        resources: List[Dict[str, str]],
    ):
        result = await coroutine
        self._report(progress, step, percent, resources=resources)
        return result

    async def _with_heartbeats(
        self,
        awaitable: Awaitable[Any],
        progress: Optional[ProgressCallback],
        stages: List[Tuple[str, int]],
        resources: Optional[List[Dict[str, str]]] = None,
        interval_seconds: float = 12.0,
    ) -> Any:
        task = asyncio.ensure_future(awaitable)
        stage_index = 0
        try:
            while not task.done():
                done, _ = await asyncio.wait(
                    {task}, timeout=interval_seconds
                )
                if done:
                    break
                step, percent = stages[stage_index % len(stages)]
                self._report(
                    progress,
                    step,
                    percent,
                    resources=resources,
                )
                stage_index += 1
            return await task
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
