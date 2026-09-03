"""Prompt builders for the five AI call kinds (R-020, R-021, R-040, R-050..R-053)."""

_LENS_SYSTEM = (
    "You are part of a single-user writing-assistance tool. "
    "You respond ONLY with valid JSON and nothing else."
)
_EXPERT_SYSTEM = (
    "You are an expert reader in a single-user writing-assistance tool. "
    "You respond ONLY with valid JSON and nothing else."
)
_REPORT_SYSTEM = (
    "You are a writing assistant turning a curated notes dump into a report "
    "draft. You respond ONLY with valid JSON and nothing else."
)
_TONE_SYSTEM = (
    "You are a copywriter in a single-user writing-assistance tool. "
    "You respond ONLY with valid JSON and nothing else."
)
_CRITIQUE_SYSTEM = (
    "You are a constructive but relentless devil's advocate. "
    "You respond ONLY with valid JSON and nothing else."
)

_MAX_DOC_CHARS = 40_000


def _bounded(text: str) -> str:
    if len(text) <= _MAX_DOC_CHARS:
        return text
    return text[:_MAX_DOC_CHARS] + "\n\n[...document truncated for length...]"


def lens_proposal_prompt(doc_path: str, doc_content: str) -> tuple[str, str]:
    system = _LENS_SYSTEM
    user = f"""Read the following Markdown document ("{doc_path}").

Propose up to 5 expert lenses that would produce interesting reading notes on
this document (for example financial, real-estate, political, or
software-engineering expertise, as the content suggests).

Return a JSON array of objects with exactly the keys "title" (short lens name)
and "rationale" (one or two sentences explaining why this lens is relevant to
this document).

Document content:
---
{_bounded(doc_content)}
---"""
    return system, user


def expert_note_prompt(doc_path: str, doc_content: str, lens_title: str) -> tuple[str, str]:
    system = f"""{_EXPERT_SYSTEM}

You are an expert approaching this document through the lens of: {lens_title}."""
    user = f"""Read the following Markdown document ("{doc_path}") as a {lens_title}
expert. Produce your own expert notes: distinct observations, questions, and
red flags that a {lens_title} specialist would notice, each self-contained and
referencing the specific passage it reacts to.

Return a JSON array of objects with exactly the key "content" (the note text,
one to four sentences).

Document content:
---
{_bounded(doc_content)}
---"""
    return system, user


def report_prompt(dump_text: str) -> tuple[str, str]:
    system = _REPORT_SYSTEM
    user = f"""Turn the curated notes dump below into the first draft of a report.

The dump is an ordered list of typed entries: [snippet] is a quoted passage
from a source document, [highlight] a highlighted passage, [human-thought] and
[ai-thought] are thoughts from the reading round. Each entry may carry a
source document path.

Write the report as ordered paragraphs. Every paragraph is plain flowing text
(no markdown headings, no bullet lists). Weave the entries into a coherent
argument; do not merely reproduce the entries.

Return a JSON array of objects with the keys "paragraph" (the paragraph text)
and optionally "source_entry_ids" (an array of the dump entry numbers this
paragraph clearly derives from, e.g. [1, 4]).

Notes dump:
---
{dump_text}
---"""
    return system, user


def tone_samples_prompt(block: str, report_context: str) -> tuple[str, str]:
    system = _TONE_SYSTEM
    user = f"""Rewrite the target paragraph below in 5 different tones. Choose
distinct tone labels that fit a written report (for example: confident,
conversational, urgent, measured, vivid, formal, blunt, warm).

The paragraph must be understood within the context of the whole report, which
is provided as other numbered paragraphs.

Return a JSON array of EXACTLY 5 objects with the keys "tone" (short label of
the tone) and "text" (the rewritten paragraph). Each rewritten paragraph keeps
the argument and substance of the original.

Report context (other paragraphs of the report):
{report_context}

Target paragraph:
---
{block}
---"""
    return system, user


def critique_prompt(block: str, report_context: str) -> tuple[str, str]:
    system = _CRITIQUE_SYSTEM
    user = f"""Critique and challenge the argument of the target paragraph below,
so the author can formulate it better. The target paragraph must be judged
within the context of the whole report (provided as other numbered
paragraphs).

Point out weak reasoning, unsupported claims, counter-arguments, missing
evidence, and rhetorical issues. Be specific and constructive; where a claim
needs support, say what kind of support.

Return a JSON object with exactly the key "critique" (the critique text,
three to eight sentences).

Report context (other paragraphs of the report):
{report_context}

Target paragraph:
---
{block}
---"""
    return system, user
