import json
from datetime import datetime, timezone

import pytest

from app.config import Settings
from app.database import GenerationRepository
from app.live_models import HeardArgument, LiveAdvice, LiveRecord, LiveSession, LiveTurn, TurnSummary
from app.live_repository import LiveRepository
from app.services.debate_framework import prepared_snapshot, motion_type_hint
from app.services.generator import compact_content
from app.services.live import LiveCoach
from app.services.markdown_exporter import MarkdownExporter
from tests.test_pack_completeness import make_result, role_speech
from app.models import RoleSpeech, SpeakerRole, StructuredResult


def test_legacy_pack_and_live_records_accept_new_optional_fields():
    result = make_result()
    assert result.motion_understanding.motion_type == ""
    record = LiveRecord(event_id="a" * 32, speaker_side="Opposition", round="1",
                        captured_at=datetime.now(timezone.utc), summary="A claim.")
    assert record.arguments == []
    assert LiveAdvice(ready_to_say="Respond.").weighing == ""


def test_explicit_type_hints_do_not_confuse_actor_and_value_forms():
    assert motion_type_hint("This House regrets celebrity culture.").startswith("Primary type: regret")
    assert motion_type_hint("This House, as a small island government, would relocate.").startswith("Primary type: actor-policy")
    assert "Primary type: actor-policy" not in motion_type_hint("This House values privacy as a right.")


def test_complete_framework_evidence_ids_and_exports():
    data = make_result().model_dump(mode="json")
    data["motion_understanding"].update(
        motion_type="Policy", status_quo="Unprotected rest time.",
        comparison_world="A feasible limit.", actor_characterization="Schools have limited time.",
        judging_criterion="Effective learning, including rest.",
    )
    data["overall_case_strategy"]["main_arguments"] = [{
        "title": "Rest", "explanation": "Compare effective learning.",
        "evidence_direction": "E1", "practice_line": "Protect rest.",
        "claim": "Protecting rest may help learning.",
        "warrant": "Limited time changes incentives. " * 100,
        "impact": "Students can learn effectively.", "comparison": "Compare with no limit.",
        "evidence_ids": ["E1", "invented"],
    }]
    result = StructuredResult.model_validate(compact_content(data))
    argument = result.overall_case_strategy.main_arguments[0]
    assert argument.evidence_ids == ["E1"]
    assert argument.warrant == data["overall_case_strategy"]["main_arguments"][0]["warrant"]
    markdown = MarkdownExporter().export(result)
    assert "Motion type:** Policy" in markdown and argument.warrant in markdown


def test_snapshot_is_complete_json_and_keeps_round_plan_and_both_burdens():
    result = make_result()
    result.summary = "A long but complete preparation sentence. " * 600
    result.role_speeches = [RoleSpeech.model_validate(role_speech(role)) for role in
                           (SpeakerRole.first, SpeakerRole.fourth)]
    encoded = prepared_snapshot(result, "reply")
    assert len(encoded) > 18000
    payload = json.loads(encoded)
    assert payload["summary"] == result.summary
    assert payload["motion_framework"]["opposition_burden"]
    assert payload["our_role_plan"]["role"] == SpeakerRole.fourth.value
    assert "speech_text" not in payload["our_role_plan"]


@pytest.mark.asyncio
async def test_heard_causal_links_are_preserved_in_permanent_summary(tmp_path):
    base = GenerationRepository(tmp_path / "causal.db")
    await base.initialize()
    repo = LiveRepository(base)
    user, _ = await base.create_guest_session()
    session = LiveSession(motion="This House would limit homework", side="Proposition", speaking_round="2")
    await repo.create(user.user_id, session)
    coach = LiveCoach(Settings(_env_file=None))
    turn = LiveTurn(event_id="a" * 32, speaker_side="Opposition", round="1",
                    text="Homework improves grades.", captured_at=datetime.now(timezone.utc))

    async def model(prompt, schema, **kwargs):
        assert json.loads(prompt)["transcript"] == turn.text
        assert "never complete" in kwargs["system_prompt"]
        return TurnSummary(summary="The speaker claims better grades.",
                           arguments=[HeardArgument(claim="Homework improves grades.",
                                                    missing_link="No causal mechanism supplied.")])
    coach.client.generate_json = model
    summary = await coach.summarize(session, turn)
    await repo.append(user.user_id, session.session_id, summary)
    stored = (await repo.records(user.user_id, session.session_id))[0]
    assert stored.arguments[0].warrant == ""
    assert stored.arguments[0].missing_link == "No causal mechanism supplied."


@pytest.mark.asyncio
@pytest.mark.parametrize("our_round,source_round,same", [
    ("2", "1", False), ("2", "2", True), ("reply", "3", False), ("3", "reply", False),
])
async def test_live_relationship_reply_poi_and_complete_text(our_round, source_round, same):
    coach = LiveCoach(Settings(_env_file=None))
    session = LiveSession(motion="This House would limit homework", side="Proposition",
                          speaking_round=our_round)
    record = LiveRecord(event_id="a" * 32, speaker_side="Proposition" if same else "Opposition",
                        round=source_round, summary="Practice may help.", captured_at=datetime.now(timezone.utc))
    complete = "Explain the causal link and compare its limited impact. " * 10

    async def model(prompt, schema, **kwargs):
        context = json.loads(prompt)
        assert context["mode"] == ("continue" if same else "rebut")
        assert "no elapsed speech time" in kwargs["system_prompt"]
        assert "not proof the claim is false" in kwargs["system_prompt"]
        return LiveAdvice(ready_to_say=complete, main_clash="Effective learning",
                          flaws=["Needs verification"], response_strategy="Concede then weigh.",
                          weighing="Compare likely benefits with lost rest.",
                          poi_hint="Why must practice happen after school?",
                          cited_record_ids=[record.event_id, "b"*32])
    coach.client.generate_json = model
    advice = await coach.advise(session, [record])
    assert advice.ready_to_say == complete.strip()
    assert advice.cited_record_ids == [record.event_id]
    assert bool(advice.poi_hint) == (not same and our_round != "reply" and source_round != "reply")
    if advice.poi_hint:
        assert "已过首分钟且尚未进入末分钟" in advice.poi_hint
    if same:
        assert advice.flaws == []


@pytest.mark.asyncio
async def test_live_overclaim_repair_uses_evidence_not_prepared_advocacy():
    coach = LiveCoach(Settings(_env_file=None))
    session = LiveSession(
        motion="This House would limit homework", side="Proposition", speaking_round="3",
        prep_context=json.dumps({"strategy": "Our benefits are guaranteed!",
                                 "evidence": [{"evidence_id": "E1", "limitations": "Correlation only."}]}),
    )
    calls = []

    async def model(prompt, schema, **kwargs):
        context = json.loads(prompt)
        calls.append(context)
        if len(calls) == 1:
            return LiveAdvice(ready_to_say="Our proposed policy will help.",
                              weighing="我方代价确定且落在全体学生。")
        assert "strategy" not in context
        assert context["evidence_with_limits"][0]["limitations"] == "Correlation only."
        assert kwargs["temperature"] == 0
        return LiveAdvice(ready_to_say="保护休息可能有益，但课堂替代效果需要验证。",
                          weighing="若课堂练习能替代，可能在保留学习效果的同时保护休息。")
    coach.client.generate_json = model
    advice = await coach.advise(session, [])
    assert len(calls) == 2
    assert "可能" in advice.weighing
    assert not coach._overstates_projection(advice)
    assert not coach._overstates_projection(LiveAdvice(ready_to_say="Respond.", weighing="收益不确定。"))
