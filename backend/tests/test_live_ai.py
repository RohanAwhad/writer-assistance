"""Live-AI smoke tests, env-gated (spec SD-16): never part of the default run.

Run with: RUN_LIVE_AI=1 uv run pytest -m live_ai
Requires RES-001 env vars in the process:
  ANTHROPIC_VERTEX_PROJECT_ID, ANTHROPIC_MODEL, ANTHROPIC_SMALL_FAST_MODEL,
  GOOGLE_VERTEX_LOCATION (or VERTEX_LOCATION), optional VERTEX_ACCESS_TOKEN /
  ANTHROPIC_BASE_URL. Each test makes real, billed model calls.
"""

import os

import pytest

from app.ai.client import AIClient, ToneSampleDraft
from app.ai.vertex import build_ai_client

pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_AI") != "1",
        reason="live AI tests are env-gated by RUN_LIVE_AI=1 (spec SD-16)",
    ),
]

LIVE_DOC = (
    "# Draft memo\n\n"
    "We should increase the marketing budget because last quarter sales were "
    "flat. The team believes brand awareness is the bottleneck. A larger "
    "campaign would fix it.\n"
)


def _client() -> AIClient:
    return build_ai_client()


def test_live_propose_lenses() -> None:
    drafts = _client().propose_lenses("memo.md", LIVE_DOC)
    assert 1 <= len(drafts) <= 5
    for draft in drafts:
        assert draft.title.strip()
        assert draft.rationale.strip()


def test_live_expert_notes() -> None:
    notes = _client().expert_notes("memo.md", LIVE_DOC, "Financial analyst")
    assert len(notes) >= 1
    for note in notes:
        assert note.content.strip()


def test_live_generate_report() -> None:
    paragraphs = _client().generate_report(
        "1. [snippet] (memo.md)\nSales were flat last quarter.\n\n"
        "2. [ai-thought]\nBudget increase needs a causal argument."
    )
    assert len(paragraphs) >= 1
    assert all(p.text.strip() for p in paragraphs)


def test_live_tone_samples_exactly_five() -> None:
    samples = _client().tone_samples(
        "A larger campaign would fix the flat sales.",
        "1. Sales were flat last quarter.\n2. Marketing budget increase is proposed.",
    )
    assert len(samples) == 5
    assert all(isinstance(s, ToneSampleDraft) for s in samples)
    assert len({s.tone.casefold() for s in samples}) == 5
    assert all(s.text.strip() for s in samples)


def test_live_critique() -> None:
    critique = _client().critique(
        "A larger campaign would fix the flat sales.",
        "1. Sales were flat last quarter.\n2. Marketing budget increase is proposed.",
    )
    assert len(critique.strip()) > 20
