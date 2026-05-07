import json

from anthropic import AsyncAnthropicVertex


client = AsyncAnthropicVertex(project_id="itpc-gcp-ai-eng-claude", region="global")
MODEL = "claude-opus-4-6@default"


async def _ask(system: str, user: str) -> str:
    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def _parse_json(text: str) -> list | dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


async def generate_lenses(content: str, filename: str) -> list[dict]:
    system = (
        "You are an expert at identifying relevant analytical perspectives for documents. "
        "Analyze the given document and return 3-5 expert 'lenses' — perspectives from which "
        "the document should be reviewed. Each lens represents a domain expert.\n\n"
        "Return ONLY a JSON array with objects containing:\n"
        '- "name": the expert role (e.g. "Financial Analyst", "Policy Advisor")\n'
        '- "perspective": a 1-2 sentence description of how this expert would read the document\n\n'
        "No markdown fences, no explanation — just the JSON array."
    )
    user = f"Filename: {filename}\n\nDocument content:\n{content}"
    return _parse_json(await _ask(system, user))


async def generate_lens_notes(content: str, lens_name: str, lens_perspective: str) -> list[dict]:
    system = (
        f"You are a {lens_name}. {lens_perspective}\n\n"
        "Read the document and produce 3-7 expert observations from your perspective. "
        "Each observation should surface an insight, risk, opportunity, or question.\n\n"
        "Return ONLY a JSON array with objects containing:\n"
        '- "content": your observation/insight (1-3 sentences)\n'
        '- "highlight": a short, exact quote from the document that this note relates to\n\n'
        "No markdown fences, no explanation — just the JSON array."
    )
    return _parse_json(await _ask(system, content))


async def generate_report(notes: list[dict], project_name: str) -> list[dict]:
    system = (
        "You are a senior report writer. Given a collection of expert notes and observations, "
        "synthesize them into a structured analytical report.\n\n"
        "Return ONLY a JSON array of report blocks, each containing:\n"
        '- "content": the text of the block (a heading or paragraph)\n'
        '- "block_type": either "heading" or "paragraph"\n\n'
        "Start with a heading block for the report title, then alternate between section headings "
        "and paragraph content. Aim for a comprehensive but concise report.\n\n"
        "No markdown fences, no explanation — just the JSON array."
    )
    notes_text = json.dumps(notes, indent=2)
    user = f"Project: {project_name}\n\nNotes to synthesize:\n{notes_text}"
    return _parse_json(await _ask(system, user))


async def generate_tone_variations(block_content: str, full_report: str) -> list[dict]:
    system = (
        "You are an expert editor. Rewrite the given paragraph in 5 different tones, "
        "preserving the core meaning but adjusting style.\n\n"
        "Return ONLY a JSON array with exactly 5 objects containing:\n"
        '- "tone_name": one of "Professional", "Conversational", "Academic", "Persuasive", "Narrative"\n'
        '- "content": the rewritten paragraph in that tone\n\n'
        "No markdown fences, no explanation — just the JSON array."
    )
    user = (
        f"Full report context:\n{full_report}\n\n"
        f"Paragraph to rewrite:\n{block_content}"
    )
    return _parse_json(await _ask(system, user))


async def generate_critique(block_content: str, full_report: str) -> dict:
    system = (
        "You are a rigorous critical thinker. Examine the given paragraph and challenge "
        "its arguments, assumptions, and logic.\n\n"
        "Return ONLY a JSON object containing:\n"
        '- "critique": a 2-4 sentence challenge to the argument or claims made\n'
        '- "suggestions": an array of 2-4 specific improvement suggestions\n'
        '- "questions": an array of 2-3 probing questions the author should consider\n\n'
        "No markdown fences, no explanation — just the JSON object."
    )
    user = (
        f"Full report context:\n{full_report}\n\n"
        f"Paragraph to critique:\n{block_content}"
    )
    return _parse_json(await _ask(system, user))
