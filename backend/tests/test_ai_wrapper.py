"""Unit tests for the AI wrapper: request payload shaping + response parsing.

All five call kinds route through the wrapper's ChatFn boundary with a mocked
function — no env vars, no network (R-004, spec SD-16).
"""

import pytest

from app.ai import prompts
from app.ai.client import ExpertNoteDraft, LensDraft, ParagraphDraft, ToneSampleDraft
from app.ai.parsers import (
    parse_critique,
    parse_expert_notes,
    parse_lenses,
    parse_report,
    parse_tone_samples,
)
from app.ai.vertex import VertexAIClient
from app.errors import AIFormatError

MODEL = "claude-big"
SMALL_MODEL = "claude-small"


def make_client(raw: str) -> tuple[VertexAIClient, list[tuple[str, str, str, int]]]:
    calls: list[tuple[str, str, str, int]] = []

    def chat(system: str, user: str, model: str, max_tokens: int) -> str:
        calls.append((system, user, model, max_tokens))
        return raw

    return VertexAIClient(chat, MODEL, SMALL_MODEL), calls


def test_propose_lenses_shapes_request_and_parses() -> None:
    raw = (
        '[{"title": "Financial", "rationale": "Numbers matter."}, '
        '{"title": "Political", "rationale": "Power matters."}]'
    )
    client, calls = make_client(raw)
    drafts = client.propose_lenses("docs/a.md", "doc body")
    assert drafts == [
        LensDraft("Financial", "Numbers matter."),
        LensDraft("Political", "Power matters."),
    ]
    system, user, model, _tokens = calls[0]
    assert model == SMALL_MODEL
    assert "docs/a.md" in user and "doc body" in user
    assert "JSON array" in user


def test_propose_lenses_rejects_empty() -> None:
    client, _ = make_client("[]")
    with pytest.raises(AIFormatError):
        client.propose_lenses("p.md", "c")


def test_expert_notes_shapes_request_and_parses() -> None:
    raw = '[{"content": "Note one."}, "Note two."]'
    client, calls = make_client(raw)
    drafts = client.expert_notes("docs/a.md", "doc body", "Financial")
    assert drafts == [ExpertNoteDraft("Note one."), ExpertNoteDraft("Note two.")]
    system, user, model, _tokens = calls[0]
    assert model == MODEL
    assert "Financial" in system and "Financial" in user
    assert "docs/a.md" in user and "doc body" in user


def test_generate_report_parses_plain_paragraphs() -> None:
    raw = '["First paragraph.", "Second paragraph."]'
    client, calls = make_client(raw)
    drafts = client.generate_report("1. [snippet] text")
    assert drafts == [ParagraphDraft("First paragraph."), ParagraphDraft("Second paragraph.")]
    _system, user, model, _tokens = calls[0]
    assert model == MODEL
    assert "1. [snippet] text" in user


def test_generate_report_parses_paragraphs_with_source_ids() -> None:
    raw = (
        '[{"paragraph": "First.", "source_entry_ids": [1, 2]}, '
        '{"paragraph": "Second.", "source_entry_ids": "1"}]'
    )
    client, _ = make_client(raw)
    drafts = client.generate_report("dump")
    assert drafts[0].text == "First."
    assert drafts[0].source_entry_ids == (1, 2)
    assert drafts[1].source_entry_ids == ()


def test_generate_report_parses_wrapped_paragraphs_object() -> None:
    raw = '{"paragraphs": ["A.", "B."]}'
    client, _ = make_client(raw)
    drafts = client.generate_report("dump")
    assert [d.text for d in drafts] == ["A.", "B."]


def test_generate_report_rejects_empty() -> None:
    client, _ = make_client("[]")
    with pytest.raises(AIFormatError):
        client.generate_report("dump")


def test_tone_samples_requires_exactly_five_distinct_tones() -> None:
    good = "[" + ",".join(f'{{"tone": "t{i}", "text": "sample {i}"}}' for i in range(5)) + "]"
    assert parse_tone_samples(good) == [ToneSampleDraft(f"t{i}", f"sample {i}") for i in range(5)]
    too_few = "[" + ",".join(f'{{"tone": "t{i}", "text": "sample {i}"}}' for i in range(4)) + "]"
    with pytest.raises(AIFormatError):
        parse_tone_samples(too_few)
    too_many = "[" + ",".join(f'{{"tone": "t{i}", "text": "sample {i}"}}' for i in range(6)) + "]"
    with pytest.raises(AIFormatError):
        parse_tone_samples(too_many)
    duplicated = (
        '[{"tone": "formal", "text": "a"}, {"tone": "formal", "text": "b"}, '
        '{"tone": "warm", "text": "c"}, {"tone": "sharp", "text": "d"}, '
        '{"tone": "calm", "text": "e"}]'
    )
    with pytest.raises(AIFormatError):
        parse_tone_samples(duplicated)


def test_tone_samples_request_carries_block_and_report_context() -> None:
    raw = "[" + ",".join(f'{{"tone": "tone{i}", "text": "sample {i}"}}' for i in range(5)) + "]"
    client, calls = make_client(raw)
    block = "Target block text."
    context = "1. First other paragraph.\n2. Second other paragraph."
    samples = client.tone_samples(block, context)
    assert len(samples) == 5
    _system, user, model, _tokens = calls[0]
    assert model == SMALL_MODEL
    assert "Target block text." in user
    assert "First other paragraph." in user and "Second other paragraph." in user
    assert "EXACTLY 5" in user


def test_critique_request_carries_block_and_report_context() -> None:
    raw = '{"critique": "The claim is unsupported."}'
    client, calls = make_client(raw)
    block = "Target block text."
    context = "1. Other paragraph."
    result = client.critique(block, context)
    assert result == "The claim is unsupported."
    _system, user, model, _tokens = calls[0]
    assert model == SMALL_MODEL
    assert "Target block text." in user
    assert "Other paragraph." in user
    assert "critique" in user.casefold()


def test_parsers_reject_malformed_output() -> None:
    with pytest.raises(AIFormatError):
        parse_lenses("not json at all")
    with pytest.raises(AIFormatError):
        parse_expert_notes('{"content": "not a list"}')
    with pytest.raises(AIFormatError):
        parse_report("42")
    with pytest.raises(AIFormatError):
        parse_tone_samples('{"tone": "x"}')
    with pytest.raises(AIFormatError):
        parse_critique('[{"critique": "x"}]')
    with pytest.raises(AIFormatError):
        parse_critique('{"missing": true}')


def test_parsers_accept_fenced_json() -> None:
    raw = '```json\n[{"title": "T", "rationale": "R"}]\n```'
    assert parse_lenses(raw) == [LensDraft("T", "R")]


def test_parse_lenses_rejects_missing_fields() -> None:
    with pytest.raises(AIFormatError):
        parse_lenses('[{"title": "T"}]')
    with pytest.raises(AIFormatError):
        parse_lenses('[{"title": "", "rationale": "R"}]')


def test_ai_wrapper_routes_all_five_call_kinds_through_chat() -> None:
    calls: list[str] = []

    def chat(system: str, user: str, model: str, max_tokens: int) -> str:
        calls.append(model)
        if "lenses that would produce" in user:
            return '[{"title": "T", "rationale": "R"}]'
        if "through the lens of" in system:
            return '[{"content": "N"}]'
        if "curated notes dump" in user:
            return '["P"]'
        if "EXACTLY 5" in user:
            return "[" + ",".join(f'{{"tone": "t{i}", "text": "s{i}"}}' for i in range(5)) + "]"
        return '{"critique": "C"}'

    client = VertexAIClient(chat, MODEL, SMALL_MODEL)
    assert client.propose_lenses("p", "c") == [LensDraft("T", "R")]
    assert client.expert_notes("p", "c", "Financial") == [ExpertNoteDraft("N")]
    assert client.generate_report("d") == [ParagraphDraft("P")]
    assert len(client.tone_samples("b", "ctx")) == 5
    assert client.critique("b", "ctx") == "C"
    assert calls == [SMALL_MODEL, MODEL, MODEL, SMALL_MODEL, SMALL_MODEL]


def test_prompt_builders_are_plain_callables() -> None:
    system, user = prompts.lens_proposal_prompt("p.md", "short doc")
    assert system and user
    assert len(user) < 10000
    system, user = prompts.expert_note_prompt("p.md", "short doc", "Legal")
    assert "Legal" in system
    system, user = prompts.report_prompt("dump text here")
    assert "dump text here" in user
    system, user = prompts.tone_samples_prompt("b", "c")
    assert "b" in user and "c" in user
    system, user = prompts.critique_prompt("b", "c")
    assert "b" in user and "c" in user


def test_prompt_builder_truncates_long_docs() -> None:
    _system, user = prompts.lens_proposal_prompt("p.md", "x" * 200_000)
    assert len(user) < 50_000
