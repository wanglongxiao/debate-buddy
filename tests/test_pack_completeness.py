import json
from datetime import datetime, timedelta

import pytest

from app.config import Settings
from app.models import (
    DebateSpeech, EvidenceExpansion, GenerateRequest, GenerateResponse, PackDetail,
    PackPatch, ResearchPlan, RoleSpeechSet, SearchResult, SpeakerRole,
    SpeechExportRequest, StructuredResult, PACK_SECTIONS,
)
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


def role_speech(role):
    return {
        "role": role, "role_focus": "Compare the strongest cases.",
        "builds_on": "Use the established team case.", "new_contribution": "Weigh likelihood and impact.",
        "rebuttals": ["An anticipated objection needs proof."],
        "main_clashes": [{
            "main_clash": "Learning versus rest", "proposition_case": "Rest improves learning.",
            "opposition_case": "Practice needs time.", "our_response": "Compare effective practice.",
            "weighing": "Probability and magnitude favor protected rest.",
        }],
        "outline": ["Explain the clash.", "Weigh outcomes."],
        "speech_text": "Compare learning benefits with the cost of lost rest. " * 20,
        "evidence_ids": ["E1"],
    }


@pytest.mark.asyncio
async def test_selected_roles_complete_ordered_and_retry_missing_role():
    service = DebateGeneratorService(Settings(_env_file=None), None)
    request = GenerateRequest(motion=make_result().motion, side="Proposition",
                              speaker_roles=[SpeakerRole.fourth, SpeakerRole.first, SpeakerRole.second])
    data = make_result().model_dump(mode="json")
    previous = role_speech(SpeakerRole.first)
    previous["role_focus"] = "Keep the user's earlier emphasis on vulnerable students."
    data["role_speeches"] = [previous]
    calls = []
    async def model(prompt, schema, **kwargs):
        context = json.loads(prompt)
        calls.append(context)
        assert schema == RoleSpeechSet
        assert context["current_role_speeches"][0]["role_focus"] == previous["role_focus"]
        assert context["selected_roles"] == [SpeakerRole.first.value, SpeakerRole.second.value, SpeakerRole.fourth.value]
        roles = [SpeakerRole.first] if len(calls) == 1 else request.speaker_roles
        return RoleSpeechSet(role_speeches=[role_speech(role) for role in roles])
    service.llm.generate_json = model
    prepared = await service._role_speeches(request, data)
    assert len(calls) == 2 and "repair" in calls[1]
    assert [item["role"] for item in prepared] == calls[1]["selected_roles"]
    data = make_result().model_dump(mode="json")
    data["role_speeches"] = prepared
    assert compact_content(data)["role_speeches"] == prepared
    exported = MarkdownExporter().export(StructuredResult.model_validate(data))
    assert all(role.value in exported for role in request.speaker_roles)
    assert "Weighing:" in exported and "Opposition:" in exported


@pytest.mark.asyncio
async def test_update_regenerates_roles_after_case_change_and_preserves_scope():
    service = DebateGeneratorService(Settings(_env_file=None), None)
    original = make_result()
    request = GenerateRequest(motion=original.motion, side="Proposition",
                              speaker_roles=[SpeakerRole.second, SpeakerRole.third])
    pack = PackDetail(generation_id="a"*32, request=request,
        latest=GenerateResponse(structured_result=original, markdown_result=""),
        created_at=datetime.now(), updated_at=datetime.now(),
        expires_at=datetime.now()+timedelta(days=360))
    calls = []
    async def model(prompt, schema, **kwargs):
        calls.append(schema)
        if schema == ResearchPlan:
            return ResearchPlan(queries=[f"rest evidence {i}" for i in range(5)])
        if schema == PackPatch:
            return PackPatch(change_summary="Clarified the case.", summary="Updated supported case.")
        assert schema == RoleSpeechSet
        return RoleSpeechSet(role_speeches=[role_speech(role) for role in request.speaker_roles])
    async def research(req, queries):
        return [], []
    service.llm.generate_json = model
    service.web_research.run = research
    updated = await service.update_pack(pack, "Clarify the case.")
    assert "role_speeches" in updated.changed_sections
    assert [item.role for item in updated.structured_result.role_speeches] == request.speaker_roles
    calls.clear()
    limited = await service.update_pack(pack, "Clarify summary only.", sections=["summary"])
    assert RoleSpeechSet not in calls
    assert limited.changed_sections == ["summary"]
    calls.clear()
    scoped_roles = await service.update_pack(pack, "Prepare selected roles.", sections=["role_speeches"])
    assert RoleSpeechSet in calls
    assert scoped_roles.changed_sections == ["role_speeches"]


@pytest.mark.asyncio
async def test_word_export_uses_only_requested_role_and_accepts_all_sections():
    SpeechExportRequest(role=SpeakerRole.fourth, sections=PACK_SECTIONS)
    service = DebateGeneratorService(Settings(_env_file=None), None)
    original = make_result()
    original.role_speeches = RoleSpeechSet(role_speeches=[
        role_speech(SpeakerRole.first), role_speech(SpeakerRole.fourth),
    ]).role_speeches
    async def model(prompt, schema, **kwargs):
        context = json.loads(prompt)
        assert [item["role"] for item in context["selected_material"]["role_speeches"]] == [SpeakerRole.fourth.value]
        assert "BOTH proposition" in kwargs["system_prompt"]
        return DebateSpeech(title="Reply", role=SpeakerRole.fourth.value, outline=["Weigh"], speech_text="Full reply.")
    service.llm.generate_json = model
    await service.export_speech(original, SpeakerRole.fourth.value, PACK_SECTIONS)


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
