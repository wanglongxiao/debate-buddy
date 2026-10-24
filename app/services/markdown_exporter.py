from app.models import StructuredResult


class MarkdownExporter:
    def export(self, result: StructuredResult) -> str:
        zh = result.language == "中文"
        titles = (
            ["速读摘要", "辩题与定义", "证据库", "核心论证", "攻防回应", "交叉质询", "开篇短稿"]
            if zh else ["Quick Summary", "Motion & Definitions", "Evidence Bank",
                        "Core Case", "Attack & Defense", "Cross Fire", "Speech Starter"]
        )
        lines = [
            "# Debate Buddy Prep Pack", "",
            f"**Motion:** {result.motion}", f"**Side:** {result.side}",
            f"**Speech time:** {result.speech_time_minutes} minutes",
            f"**Roles:** {', '.join(result.speaker_roles)}", "",
        ]

        def heading(index):
            lines.extend(["", f"## {index + 1}. {titles[index]}", ""])

        heading(0)
        lines.append(result.summary or result.overall_case_strategy.one_sentence_stance)
        heading(1)
        motion = result.motion_understanding
        lines.extend([motion.plain_meaning, f"**Clash:** {motion.main_clash}",
                      f"**Proposition:** {motion.proposition_burden}",
                      f"**Opposition:** {motion.opposition_burden}"])
        for item in result.definitions:
            lines.append(f"- **{item.term}:** {item.recommended_definition}")
        heading(2)
        if not result.evidence_bank:
            lines.append("No sourced evidence available; verify claims before use.")
        for item in result.evidence_bank:
            lines.extend([
                f"### {item.evidence_id}: {item.claim}",
                f"**Dimension:** {item.aspect}" if item.aspect else "",
                item.evidence_summary,
                f"**Source:** [{item.source_title}]({item.source_url})",
                f"**Date / type:** {item.published_date_or_accessed_at} · {item.source_type} · {item.credibility}",
            ])
            for title, value in [
                ("Source excerpt", item.source_excerpt),
                ("Context / method", item.context_and_method),
                ("Limitations", item.limitations),
                ("Use in our case", item.why_it_helps_our_side),
                ("Say", item.simple_practice_line),
            ]:
                if value:
                    lines.append(f"**{title}:** {value}")
            lines.append("")
        heading(3)
        case = result.overall_case_strategy
        lines.append(case.one_sentence_stance)
        for item in case.main_arguments:
            lines.extend([f"### {item.title}", item.explanation,
                          f"**Evidence:** {item.evidence_direction}",
                          f'**You can say:** "{item.practice_line}"'])
        lines.append(f"**Main risk:** {case.most_vulnerable_argument}")
        heading(4)
        for item in result.attack_defense_map:
            lines.extend([f"**They may argue:** {item.opponent_point}",
                          f"**Respond:** {item.our_response}", ""])
        heading(5)
        for item in result.cross_fire.questions:
            lines.extend([f"**Ask:** {item.question}",
                          f"**If yes:** {item.follow_up_if_yes}",
                          f"**If no:** {item.follow_up_if_no}", ""])
        heading(6)
        lines.append(result.first_speaker_speech.speech_text)
        return "\n".join(lines)

    @staticmethod
    def _table(value):
        return value.replace("|", "\\|").replace("\n", " ")
