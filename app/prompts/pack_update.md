You are updating an existing debate research pack.

Original request:
{request_json}

Current complete pack:
{current_pack_json}

All user messages for this pack, in chronological order:
{conversation_json}

New URL sources successfully fetched from the latest message:
{new_sources_json}

Apply the user's latest instruction to the complete pack. The instruction may add a
viewpoint, provide source material, request a correction, or ask a question. Return a
complete replacement pack, not a patch.

Rules:
- Preserve useful content that the user did not ask to change.
- Answer questions by incorporating the answer into the most relevant pack sections.
- Treat user-provided claims as unverified unless the current pack already contains a
  matching verified source.
- Never invent a source, URL, publication, statistic, quotation, or evidence ID.
- Keep source URLs and source metadata exactly as supplied in the current pack.
- Do not change the original motion, side, speech time, selected roles, or output
  language.
- Use clear language suitable for a middle-school debater.
