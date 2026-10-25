"""Shared, curated WSD coaching guidance for preparation and live debate.

Training material: user-supplied HMDC WSD glossary and speaker notes.
Rules cross-check: WSDC Board Speaker Training (adapted Serbia 2024),
https://www.wsdcdebating.org/_files/ugd/669183_97fad98c6ab6452e9dd587a18ca9f953.pdf
https://hmdcforensics.com/wsd-resources/
Examples in training notes are illustrations, never a factual evidence source.
"""

WSD_COACHING = """
Use this shared WSD reasoning framework, adapted to the actual motion:
MOTION AND BURDENS: identify policy, actor-policy, value, comparison, regret,
prediction or mixed motion; explain the classification, never force all topics
into a policy model. An explicit 'as [actor]' or actor-perspective decision is
actor-policy, even when it also involves policy or comparison: name actor-policy
as the primary type. Policy compares a specified workable change against the
status quo or a plausible opposition alternative, including implementation.
Actor-policy asks what THIS actor should do given its knowledge, interests,
incentives, resources and constraints; do not give the actor omniscience.
Value motions require a defensible evaluative criterion, not an invented policy.
Comparison requires equivalent scope and a common criterion for both worlds.
Regret compares the actual development against a plausible world without it,
considering benefits lost too; it does not automatically propose a future ban.
An explicit 'This House regrets' motion has REGRET as its primary type, even
though it also evaluates values. Do not label it only as a value motion.
Prediction asks likelihood of the specified future, not whether it is desirable.
State two motion-specific burdens. Opposition can defeat a necessary proposition
burden or show a better comparison; it need not prove the exact opposite of every
claim. Characterize affected actors and explain their behavior, not stereotypes.
Do not invent the actual baseline, current behavior, legal powers or prevalence.
If sources do not establish them, label the baseline/characterization as a scenario
assumption or an unknown to verify. Proposition need not prove its alternative
perfect or the status quo worthless; prove the relevant comparative advantage.
Opposition may defeat that necessary comparison without proving every opposite
claim. Separate required burdens from optional routes to winning them.
FRAMING: define contested terms fairly within ordinary meaning; no narrowing
that excludes reasonable opposition. First opposition rebuts and challenges only
an unfair definition, explaining why and offering a fair replacement. Show how
the main clash and judging criterion answer the motion. Caseline must link the
whole team's why and how, with numbered signposts and transitions.
ARGUMENTS: tagline -> precise claim -> relevant evidence -> warrant/mechanism ->
impact -> comparison. Explain each causal link: why actors respond, under what
conditions, who is affected and why the consequence meets our burden. Evidence
alone is not a warrant. Preserve uncertainty, source scope and causal limits.
REBUTTAL: fairly state their strongest specific claim, identify the exact premise,
causal link, evidence relevance or impact to contest, then explain why it fails.
Distinguish direct refutation, mitigation (smaller/less likely), concession plus
weighing, and turning their reasoning. A missing citation is a verification gap,
not proof the claim is false. Do not strawman or replace rebuttal with our slogan.
If their point is sound, concede its limited force and compare competing impacts.
WEIGHING: group the debate into 2-3 decisive clashes; develop both sides fairly.
Choose relevant magnitude, probability, time, distribution, reversibility or
principle criteria and explain WHY one takes priority in THIS motion; no checklist.
Explain why our answer wins the necessary burden even if we lose a smaller clash.
ROLES: first lays foundations; second rebuts and substantively extends; third
prioritizes rebuttal and clash comparison; reply crystallizes the whole debate.
Our preparation strategy reserves the third core argument for second and adds
no new independent argument in third, no new facts/independent arguments in reply.
These are conservative coaching choices, not claims of universal rule prohibitions:
WSDC allows a third-speaker argument flagged in first; reply may add derivative
weighing/framing/examples from established material, not an independent new case.
POI: one short relevant challenge that tests a premise or consequence. Under WSD
rules POIs are only between the first and last minute of substantive speeches,
max 15 seconds, never during reply. If timing/format is unknown, make permission
conditional; do not infer elapsed time from a round number or recommend interrupting
now. Accepting about two is coaching guidance, not an automatic-loss threshold.
DELIVERY: clear simple words, numbered signposts, concise transitions. Prioritize
reasoning and strategic engagement; rhetoric cannot substitute for a warranted case.
"""

PACK_FRAMEWORK = WSD_COACHING + """
Populate motion_understanding.motion_type with the type and brief reason;
status_quo with the relevant baseline; comparison_world with a plausible alternative;
actor_characterization with actors' incentives and constraints; judging_criterion
with the decisive framing criterion. Keep each field short but motion-specific.
Each main argument needs a precise claim, a developed causal warrant, impact and
comparison in its structured fields, and valid evidence_ids (or empty if unsourced).
explanation ties the chain together; do not repeat entire field text there.
Each attack_defense item needs response_type (in requested language), target_link
(the specific premise/mechanism/impact challenged), and weighing that resolves the
clash rather than merely naming criteria. Training examples supply no evidence.
"""


def motion_type_hint(motion):
    """Anchor unambiguous WSD forms; leave ambiguous classification to reasoning."""
    import re

    text = motion.lower()
    if re.search(r"^(?:(?:this house|th)\s+)?regrets?\b", text) or "后悔" in text or "遗憾" in text:
        return "Primary type: regret. Compare the actual development with a plausible world without it; include lost benefits."
    if re.search(r"(?:^(?:this house|th)\s*,?\s*as\b|^as\b)", text) or "作为" in text:
        return "Primary type: actor-policy. Evaluate the specified actor's decision with its own knowledge, incentives and constraints."
    return "Classify from the actual motion; distinguish policy, value, comparison and prediction. Do not force a policy model."


def prepared_snapshot(structured, speaking_round):
    """Complete JSON of essential prep; avoid truncating serialized JSON mid-value."""
    import json

    roles = {
        "1": "1st Speaker", "2": "2nd Speaker", "3": "3rd Speaker",
        "4": "4th Speaker / Reply Speaker / Summary Speaker",
        "reply": "4th Speaker / Reply Speaker / Summary Speaker",
    }
    selected = next((r for r in structured.role_speeches
                     if r.role.value == roles.get(speaking_round)), None)
    return json.dumps({
        "prepared_side": structured.side,
        "summary": structured.summary,
        "motion_framework": structured.motion_understanding.model_dump(mode="json"),
        "definitions": [d.model_dump(mode="json") for d in structured.definitions[:3]],
        "strategy": structured.overall_case_strategy.model_dump(mode="json"),
        "attack_defense": [p.model_dump(mode="json") for p in structured.attack_defense_map[:4]],
        "evidence": [e.model_dump(mode="json", exclude={"source_excerpt", "simple_practice_line"})
                     for e in structured.evidence_bank[:10]],
        "our_role_plan": selected.model_dump(mode="json", exclude={"speech_text"}) if selected else None,
        "note": "Preparation only; no proof these arguments were delivered live. "
                "Prepared material may be for the other side; adapt to our_side.",
    }, ensure_ascii=False)
