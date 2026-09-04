"""Live DeepSeek smoke tests, env-gated (spec SD-16): never part of the default run.

Run with: RUN_LIVE_AI=1 uv run pytest tests/test_live_deepseek.py -m live_ai
Requires DEEPSEEK_API_KEY in the process (optional DEEPSEEK_MODEL; falls back
to deepseek-v4-flash). Each test makes real, billed calls to api.deepseek.com
through the DeepSeekAIClient transport. The API key is only used in the
Authorization header and is never logged or printed.
"""

import os

import pytest

from app.ai.client import AIClient, ExpertNoteDraft, LensDraft, ToneSampleDraft
from app.ai.deepseek import build_ai_client

pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_AI") != "1" or not os.environ.get("DEEPSEEK_API_KEY"),
        reason=(
            "live DeepSeek tests are env-gated by RUN_LIVE_AI=1 and "
            "DEEPSEEK_API_KEY (spec SD-16)"
        ),
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


def test_live_deepseek_propose_lenses() -> None:
    drafts = _client().propose_lenses("memo.md", LIVE_DOC)
    assert 1 <= len(drafts) <= 5
    for draft in drafts:
        assert isinstance(draft, LensDraft)
        assert draft.title.strip()
        assert draft.rationale.strip()


def test_live_deepseek_expert_notes() -> None:
    notes = _client().expert_notes("memo.md", LIVE_DOC, "Financial analyst")
    assert len(notes) >= 1
    for note in notes:
        assert isinstance(note, ExpertNoteDraft)
        assert note.content.strip()


def test_live_deepseek_tone_samples_exactly_five() -> None:
    samples = _client().tone_samples(
        "A larger campaign would fix the flat sales.",
        "1. Sales were flat last quarter.\n2. Marketing budget increase is proposed.",
    )
    assert len(samples) == 5
    assert all(isinstance(s, ToneSampleDraft) for s in samples)
    assert len({s.tone.casefold() for s in samples}) == 5
    assert all(s.text.strip() for s in samples)
