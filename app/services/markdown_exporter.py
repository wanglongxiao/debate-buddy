from app.models import StructuredResult


class MarkdownExporter:
    def export(self, result: StructuredResult) -> str:
        zh = result.language == "中文"
        titles = (
            ["速读摘要", "辩题与定义", "各角色准备稿", "证据库", "核心论证", "攻防回应", "交叉质询"]
            if zh else ["Quick Summary", "Motion & Definitions", "Speaker Roles", "Evidence Bank",
                        "Core Case", "Attack & Defense", "Cross Fire"]
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
        for label, value in [
            ("Motion type", motion.motion_type), ("Baseline", motion.status_quo),
            ("Comparison world", motion.comparison_world),
            ("Actors / incentives", motion.actor_characterization),
            ("Judging criterion", motion.judging_criterion),
        ]:
            if value:
                lines.append(f"**{label}:** {value}")
        for item in result.definitions:
            lines.append(f"- **{item.term}:** {item.recommended_definition}")
        heading(2)
        lines.extend(self._role_lines(result))
        heading(3)
        if not result.evidence_bank:
            lines.append("暂无有来源的证据；请核实相关主张后再使用。" if zh else
                         "No sourced evidence available; verify claims before use.")
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
        heading(4)
        case = result.overall_case_strategy
        lines.append(case.one_sentence_stance)
        for item in case.main_arguments:
            lines.extend([f"### {item.title}", item.explanation])
            for label, value in [("Claim", item.claim), ("Why it follows", item.warrant),
                                 ("Impact", item.impact), ("Comparison", item.comparison)]:
                if value:
                    lines.append(f"**{label}:** {value}")
            lines.extend([f"**Evidence IDs:** {', '.join(item.evidence_ids)}" if item.evidence_ids else "",
                          f"**Evidence:** {item.evidence_direction}",
                          f'**You can say:** "{item.practice_line}"'])
        lines.append(f"**Main risk:** {case.most_vulnerable_argument}")
        heading(5)
        for item in result.attack_defense_map:
            lines.extend([f"**They may argue:** {item.opponent_point}",
                          f"**Respond:** {item.our_response}", ""])
            for label, value in [("Response approach", item.response_type),
                                 ("Link to challenge", item.target_link), ("Weighing", item.weighing)]:
                if value:
                    lines.append(f"**{label}:** {value}")
        heading(6)
        for item in result.cross_fire.questions:
            lines.extend([f"**Ask:** {item.question}",
                          f"**If yes:** {item.follow_up_if_yes}",
                          f"**If no:** {item.follow_up_if_no}", ""])
        if zh:
            labels = {
                "Motion": "辩题", "Side": "立场", "Speech time": "发言时间", "Roles": "辩位",
                "Clash": "主要争点", "Proposition": "正方", "Opposition": "反方",
                "Motion type": "辩题类型", "Baseline": "现状基线",
                "Comparison world": "比较世界", "Actors / incentives": "角色与动机",
                "Judging criterion": "评判标准", "Dimension": "维度", "Source": "来源",
                "Date / type": "日期与类型", "Source excerpt": "来源原文",
                "Context / method": "背景与方法", "Limitations": "局限",
                "Use in our case": "对我方的帮助", "Say": "可以这样说", "Claim": "主张",
                "Why it follows": "因果机制", "Impact": "影响", "Comparison": "双方世界比较",
                "Evidence IDs": "证据编号", "Evidence": "证据", "You can say": "可以这样说",
                "Main risk": "主要风险", "They may argue": "对方可能主张",
                "Respond": "回应", "Response approach": "回应方式", "Link to challenge": "需要反驳的环节",
                "Weighing": "比较与权衡", "Ask": "提问", "If yes": "如果回答是", "If no": "如果回答否",
                "Role focus": "角色重点", "Builds on": "承接前序", "Contribution": "递进贡献",
                "Anticipated rebuttal": "预期反驳", "Our response": "我方回应", "Speech outline": "发言提纲",
            }
            for index, line in enumerate(lines):
                for english, chinese in labels.items():
                    marker = f"**{english}:**"
                    if line.startswith(marker) or line.startswith(f"- {marker}"):
                        line = line.replace(marker, f"**{chinese}:**", 1)
                        break
                if line.startswith("#### Main clash:"):
                    line = line.replace("#### Main clash:", "#### 主要争点:", 1)
                if line.startswith("**发言时间:**"):
                    line = line.replace(" minutes", " 分钟")
                if line == "**Speech outline:**":
                    line = "**发言提纲:**"
                lines[index] = line
        return "\n".join(lines)

    @staticmethod
    def _role_lines(result):
        lines = []
        if not result.role_speeches:
            lines.append(result.first_speaker_speech.speech_text)
        for item in result.role_speeches:
            lines.extend([
                f"### {item.role.value}", f"**Role focus:** {item.role_focus}",
                f"**Builds on:** {item.builds_on}", f"**Contribution:** {item.new_contribution}",
                *[f"- **Anticipated rebuttal:** {text}" for text in item.rebuttals],
            ])
            for clash in item.main_clashes:
                lines.extend([
                    f"#### Main clash: {clash.main_clash}",
                    f"**Proposition:** {clash.proposition_case}",
                    f"**Opposition:** {clash.opposition_case}",
                    f"**Our response:** {clash.our_response}",
                    f"**Weighing:** {clash.weighing}",
                ])
            lines.extend(["**Speech outline:**", *[f"- {text}" for text in item.outline],
                          "", item.speech_text, f"**Evidence IDs:** {', '.join(item.evidence_ids)}", ""])
        return lines

    @staticmethod
    def _table(value):
        return value.replace("|", "\\|").replace("\n", " ")
