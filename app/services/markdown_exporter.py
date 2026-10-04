from app.models import StructuredResult


class MarkdownExporter:
    def export(self, result: StructuredResult) -> str:
        lines = [
            "# Debate Buddy Prep Pack",
            "",
            f"**Motion:** {result.motion}",
            f"**Side:** {result.side}",
            f"**Speech time:** {result.speech_time_minutes} minutes",
            f"**Roles:** {', '.join(result.speaker_roles)}",
            "",
            "## 1. Motion Understanding",
            "",
            result.motion_understanding.plain_meaning,
            "",
            f"**Main clash:** {result.motion_understanding.main_clash}",
            f"**Proposition must prove:** {result.motion_understanding.proposition_burden}",
            f"**Opposition must prove:** {result.motion_understanding.opposition_burden}",
            "",
            "### Key concepts",
        ]
        for item in result.motion_understanding.key_concepts:
            lines.append(f"- **{item.term}:** {item.simple_explanation}")
        self._bullet_section(
            lines,
            "Easy attacks against the opponent",
            result.motion_understanding.easy_attacks_against_opponent,
        )
        self._bullet_section(
            lines, "Risks for our side", result.motion_understanding.risks_for_our_side
        )

        lines.extend(["", "## 2. Definitions", ""])
        for item in result.definitions:
            lines.extend(
                [
                    f"### {item.term}",
                    f"- **Possible definitions:** {'; '.join(item.possible_definitions)}",
                    f"- **Recommended:** {item.recommended_definition}",
                    f"- **Why it helps:** {item.why_it_helps}",
                    f"- **Possible challenge:** {item.possible_challenge}",
                    "",
                ]
            )

        strategy = result.overall_case_strategy
        lines.extend(
            [
                "## 3. Overall Case Strategy",
                "",
                f"**Our stance:** {strategy.one_sentence_stance}",
                "",
            ]
        )
        for index, argument in enumerate(strategy.main_arguments, start=1):
            lines.extend(
                [
                    f"### Argument {index}: {argument.title}",
                    argument.explanation,
                    f"- **Evidence direction:** {argument.evidence_direction}",
                    f'- **You can say:** "{argument.practice_line}"',
                    "",
                ]
            )
        lines.extend(
            [
                f"**Strongest argument:** {strategy.strongest_argument}",
                f"**Most vulnerable argument:** {strategy.most_vulnerable_argument}",
            ]
        )
        self._bullet_section(lines, "Emphasize", strategy.emphasize)
        self._bullet_section(lines, "Avoid", strategy.avoid)

        lines.extend(
            [
                "",
                "## 4. Attack and Defense Map",
                "",
                "| Opponent point | Our attack or risk | Our response | Practice line |",
                "|---|---|---|---|",
            ]
        )
        for item in result.attack_defense_map:
            cells = [
                item.opponent_point,
                item.our_attack_or_risk,
                item.our_response,
                item.practice_line,
            ]
            lines.append("| " + " | ".join(self._table(value) for value in cells) + " |")

        lines.extend(["", "## 5. Cross Fire", ""])
        self._bullet_section(lines, "Goals", result.cross_fire.goals)
        for index, item in enumerate(result.cross_fire.questions, start=1):
            lines.extend(
                [
                    f"### Question {index}",
                    f'**Ask:** "{item.question}"',
                    f"- **Purpose:** {item.purpose}",
                    f"- **If yes:** {item.follow_up_if_yes}",
                    f"- **If no:** {item.follow_up_if_no}",
                    f"- **Best for:** {item.best_for}",
                    "",
                ]
            )
        self._bullet_section(lines, "Keep emphasizing", result.cross_fire.emphasize)
        self._bullet_section(lines, "Avoid", result.cross_fire.avoid)

        lines.extend(["", "## 6. Team Debate Outline", ""])
        team_items = [
            ("1st Speaker", result.team_outline.first_speaker),
            ("2nd Speaker", result.team_outline.second_speaker),
            ("3rd Speaker", result.team_outline.third_speaker),
            ("4th / Reply Speaker", result.team_outline.fourth_speaker),
        ]
        for title, item in team_items:
            lines.append(f"### {title}")
            self._bullet_section(lines, "Main tasks", item.main_tasks)
            self._bullet_section(lines, "Avoid", item.avoid)

        lines.extend(["", "## 7. Detailed 1st Speaker Speech", ""])
        self._bullet_section(
            lines, "Outline", result.first_speaker_speech.outline
        )
        lines.extend(["", result.first_speaker_speech.speech_text, ""])

        lines.extend(["", "## 8. My Role Deep Research", ""])
        for role in result.my_role_research:
            lines.append(f"### {role.role}")
            self._bullet_section(lines, "Role tasks", role.role_tasks)
            self._bullet_section(lines, "Key points", role.key_points)
            for argument in role.detailed_arguments:
                lines.extend(
                    [
                        f"#### {argument.title}",
                        argument.explanation,
                        f"- **Evidence direction:** {argument.evidence_direction}",
                        f'- **You can say:** "{argument.practice_line}"',
                    ]
                )
            self._bullet_section(
                lines, "Evidence IDs", role.supporting_evidence_ids
            )
            self._bullet_section(lines, "Possible attacks", role.possible_attacks)
            self._bullet_section(lines, "Responses", role.responses)
            self._bullet_section(lines, "Speech outline", role.speech_outline)
            lines.extend(["", role.speech_text, ""])

        lines.extend(["", "## 9. Evidence Bank", ""])
        if not result.evidence_bank:
            lines.append(
                "_No verified web evidence was available. Do not present unsupported claims as facts._"
            )
        for item in result.evidence_bank:
            lines.extend(
                [
                    f"### {item.evidence_id}: {item.claim}",
                    f"- **Fact:** {item.evidence_summary}",
                    f"- **Source:** [{item.source_title}]({item.source_url})",
                    f"- **Date:** {item.published_date_or_accessed_at}",
                    f"- **Source type:** {item.source_type}",
                    f"- **Credibility:** {item.credibility}",
                    f"- **Why it helps:** {item.why_it_helps_our_side}",
                    f'- **You can say:** "{item.simple_practice_line}"',
                    "",
                ]
            )

        lines.extend(["", "## 10. Simple Vocabulary Builder", ""])
        lines.extend(
            [
                "| Word | Simple English | 中文 | Example | Debate word? |",
                "|---|---|---|---|---|",
            ]
        )
        for item in result.vocabulary_builder:
            lines.append(
                "| "
                + " | ".join(
                    self._table(value)
                    for value in [
                        item.word,
                        item.simple_english,
                        item.chinese,
                        item.example_sentence,
                        "Yes" if item.debate_useful else "No",
                    ]
                )
                + " |"
            )

        lines.extend(["", "## 11. Practice Plan", ""])
        self._bullet_section(lines, "Today", result.practice_plan.today)
        self._bullet_section(lines, "Tomorrow", result.practice_plan.tomorrow)
        self._bullet_section(
            lines, "Before the tournament", result.practice_plan.before_tournament
        )
        self._bullet_section(
            lines, "Learning from YouTube", result.practice_plan.youtube_learning
        )
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _bullet_section(lines: list[str], title: str, items: list[str]) -> None:
        lines.extend(["", f"### {title}"])
        lines.extend(f"- {item}" for item in items)

    @staticmethod
    def _table(value: str) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
