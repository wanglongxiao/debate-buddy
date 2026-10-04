import json
import re

from pydantic import BaseModel, Field

from app.llm_client import LLMResponseError, ModelArkClient
from app.models import EvidenceItem, GenerateRequest, SearchResult


class EvidenceEvaluationResult(BaseModel):
    evidence_bank: list[EvidenceItem] = Field(default_factory=list)


class EvidenceEvaluatorSkill:
    def __init__(self, llm: ModelArkClient):
        self.llm = llm

    async def run(
        self, request: GenerateRequest, sources: list[SearchResult]
    ) -> list[EvidenceItem]:
        if not sources:
            return []

        source_payload = []
        for index, source in enumerate(sources, start=1):
            source_data = source.model_dump(mode="json")
            source_data["snippet"] = source.snippet[:1200]
            source_payload.append(
                {
                    "source_id": f"S{index}",
                    **source_data,
                }
            )
        template = self.llm.read_prompt("evidence_evaluation.md")
        prompt = template.format(
            request_json=json.dumps(request.model_dump(mode="json"), ensure_ascii=False),
            sources_json=json.dumps(source_payload, ensure_ascii=False),
        )
        try:
            result = await self.llm.generate_json(
                prompt,
                EvidenceEvaluationResult,
                temperature=0.1,
                max_tokens=5000,
            )
        except LLMResponseError:
            return self._source_only_fallback(request, sources)

        allowed_urls = {source.url.rstrip("/"): source for source in sources}
        verified: list[EvidenceItem] = []
        for item in result.evidence_bank:
            source = allowed_urls.get(item.source_url.rstrip("/"))
            if source is None:
                continue
            item.source_title = source.title
            item.source_url = source.url
            item.source_type = source.source_type
            item.credibility = source.credibility
            item.published_date_or_accessed_at = (
                source.published_date or source.accessed_at.isoformat()
            )
            verified.append(item)
        return verified

    @staticmethod
    def _source_only_fallback(
        request: GenerateRequest, sources: list[SearchResult]
    ) -> list[EvidenceItem]:
        ignored_motion_words = {
            "against",
            "believes",
            "house",
            "middle",
            "motion",
            "schools",
            "should",
            "that",
            "this",
            "would",
        }
        motion_terms = {
            word
            for word in re.findall(r"[a-z]{4,}", request.motion.lower())
            if word not in ignored_motion_words
        }
        relevant = [
            source
            for source in sources
            if not motion_terms
            or any(term in source.title.lower() for term in motion_terms)
        ]
        selected_sources = relevant or sources
        evidence: list[EvidenceItem] = []
        for source in selected_sources:
            summary = " ".join(source.snippet.split())[:500]
            if not summary:
                continue
            evidence.append(
                EvidenceItem(
                    evidence_id=f"E{len(evidence) + 1}",
                    claim=f"Source material: {source.title}",
                    evidence_summary=summary,
                    source_title=source.title,
                    source_url=source.url,
                    published_date_or_accessed_at=(
                        source.published_date or source.accessed_at.isoformat()
                    ),
                    source_type=source.source_type,
                    credibility=source.credibility,
                    why_it_helps_our_side=(
                        "Use this source to check a related fact before the debate. "
                        "Read the original page before quoting it."
                    ),
                    simple_practice_line=(
                        "This source gives background information that we should verify "
                        "before using."
                    ),
                )
            )
        return evidence
