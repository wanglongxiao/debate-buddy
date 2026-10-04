Write debate speeches for a Grade 7 student.

REQUEST
{request_json}

TARGET LENGTH FOR EACH FULL SPEECH
About {target_words} words. Clear delivery matters more than reaching the exact count.

MOTION ANALYSIS
{analysis_json}

TEAM CASE
{case_json}

VERIFIED EVIDENCE
{evidence_json}

Requirements:
- Always provide a detailed first-speaker outline and speech, even when that role was not selected.
- The first speech must include greeting, motion, fair definitions, team stance, case split,
  argument 1, argument 2, and a short conclusion.
- Return one separate role-research object for every selected speaker role, using the exact role name.
- For each selected role, include tasks, 2 or 3 key points, detailed arguments, likely attacks,
  responses, outline, and a useful speech text.
- supporting_evidence_ids may contain only IDs from VERIFIED EVIDENCE. Use an empty list if none fits.
- Never add a statistic or study that is absent from VERIFIED EVIDENCE.
- Use natural spoken sentences. Keep most sentences under 18 words.
- For Chinese output, explain in Chinese but keep useful English practice lines.
- For Bilingual output, keep translations concise so the student is not overwhelmed.
