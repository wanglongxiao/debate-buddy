import json

import pytest

from app.config import Settings
from app.models import EvidenceExpansion, GenerateRequest, SearchResult, StructuredResult
from app.services.generator import DebateGeneratorService, compact_content
from app.services.markdown_exporter import MarkdownExporter


def make_result():
    return StructuredResult.model_validate({
        "motion": "This House would protect students' rest time.",
        "side": "Proposition", "speech_time_minutes": 4,
        "speaker_roles": ["1st Speaker"], "language": "English",
        "motion_understanding": {
            "plain_meaning": "Protect rest time.", "main_clash": "Learning and rest.",
            "proposition_burden": "Show benefits.", "opposition_burden": "Show harms.",
        },
        "overall_case_strategy": {
            "one_sentence_stance": "Rest matters.", "strongest_argument": "",
            "most_vulnerable_argument": "Implementation.",
        },
        "cross_fire": {}, "first_speaker_speech": {"speech_text": "We support rest."},
        "evidence_bank": [{
            "evidence_id": "E1", "claim": "Sleep supports learning.",
            "evidence_summary": "A study discusses sleep and learning.",
            "source_title": "Sleep study", "source_url": "https://example.edu/study",
            "published_date_or_accessed_at": "2026-10-24", "source_type": "University",
            "credibility": "High", "why_it_helps_our_side": "Rest has value.",
            "simple_practice_line": "Protect rest time.",
        }],
    })


def test_complete_prose_and_evidence_are_not_truncated():
    original = make_result()
    data = original.model_dump(mode="json")
    data["summary"] = "完整论证。" * 200
    template = data["evidence_bank"][0]
    data["evidence_bank"] = [
        {**template, "evidence_id": f"E{i}", "aspect": f"Dimension {i}",
         "source_url": f"https://example.edu/{i}"} for i in range(1, 12)
    ]
    normalized = compact_content(data)
    assert normalized["summary"] == data["summary"]
    assert len(normalized["evidence_bank"]) == 11
    markdown = MarkdownExporter().export(type(original).model_validate(normalized))
    assert "E11:" in markdown and data["summary"] in markdown


@pytest.mark.asyncio
async def test_existing_bank_leaves_room_for_new_researched_dimensions():
    service = DebateGeneratorService(Settings(_env_file=None), None)
    original = make_result()
    template = original.evidence_bank[0].model_dump(mode="json")
    old = [
        type(original.evidence_bank[0]).model_validate({
            **template, "evidence_id": f"E{i}", "aspect": f"Dimension {i}",
            "source_url": f"https://old.edu/{i}",
        }) for i in range(1, 9)
    ]
    sources = [
        SearchResult(title=f"Fresh {i}", url=f"https://new.edu/{i}",
                     snippet="A concrete fresh finding.") for i in range(5)
    ]

    async def model(prompt, schema, **kwargs):
        context = json.loads(prompt)
        assert context["new_request"] == "Add AI and diplomacy"
        assert len(context["new_source_urls"]) == 5
        assert schema == EvidenceExpansion
        return EvidenceExpansion(evidence_bank=[
            {**template, "evidence_id": f"E{i+9}", "aspect": f"New dimension {i}",
             "source_url": source.url, "source_excerpt": source.snippet}
            for i, source in enumerate(sources)
        ])

    service.llm.generate_json = model
    request = GenerateRequest(
        motion=original.motion, side=original.side, speaker_roles=["1st Speaker"],
        source_material="Add AI and diplomacy",
    )
    expanded = await service._expand_evidence(
        request, [e.model_dump(mode="json") for e in old], sources, existing=old,
    )
    assert {e["source_url"] for e in expanded} >= {s.url for s in sources}
    assert {e["evidence_id"] for e in expanded} >= {e.evidence_id for e in old}
