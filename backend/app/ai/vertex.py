"""Live AnthropicVertex backend behind the AIClient contract (R-004).

Env vars per RES-001: ANTHROPIC_VERTEX_PROJECT_ID, ANTHROPIC_MODEL,
ANTHROPIC_SMALL_FAST_MODEL, and the Vertex region as GOOGLE_VERTEX_LOCATION
(with VERTEX_LOCATION accepted as a fallback; GOOGLE_VERTEX_LOCATION wins).
Optional pass-through: VERTEX_ACCESS_TOKEN and ANTHROPIC_BASE_URL when set.

The AnthropicVertex SDK client is never imported by other modules; this module
owns that import so the rest of the app (and all default tests) stays offline.
"""

import os
from collections.abc import Callable, Mapping

from anthropic import AnthropicVertex
from anthropic.types import TextBlock

from app.ai import prompts
from app.ai.client import (
    AIClient,
    ExpertNoteDraft,
    LensDraft,
    ParagraphDraft,
    ToneSampleDraft,
)
from app.ai.parsers import (
    parse_critique,
    parse_expert_notes,
    parse_lenses,
    parse_report,
    parse_tone_samples,
)
from app.errors import ConfigError

ChatFn = Callable[[str, str, str, int], str]
"""ChatFn(system, user, model, max_tokens) -> assistant text."""

ENV_PROJECT_ID = "ANTHROPIC_VERTEX_PROJECT_ID"
ENV_MODEL = "ANTHROPIC_MODEL"
ENV_SMALL_MODEL = "ANTHROPIC_SMALL_FAST_MODEL"
ENV_REGION = "GOOGLE_VERTEX_LOCATION"
ENV_REGION_FALLBACK = "VERTEX_LOCATION"
ENV_ACCESS_TOKEN = "VERTEX_ACCESS_TOKEN"
ENV_BASE_URL = "ANTHROPIC_BASE_URL"

REQUIRED_ENV_VARS = (ENV_PROJECT_ID, ENV_MODEL, ENV_SMALL_MODEL)

MAX_TOKENS_LENSES = 1024
MAX_TOKENS_EXPERT = 4096
MAX_TOKENS_REPORT = 8192
MAX_TOKENS_TONE = 2048
MAX_TOKENS_CRITIQUE = 2048


class VertexSettings:
    def __init__(
        self,
        project_id: str,
        region: str,
        model: str,
        small_model: str,
        base_url: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.project_id = project_id
        self.region = region
        self.model = model
        self.small_model = small_model
        self.base_url = base_url
        self.access_token = access_token


def vertex_region(environ: Mapping[str, str]) -> str | None:
    """Region: GOOGLE_VERTEX_LOCATION wins over VERTEX_LOCATION when both set."""
    return environ.get(ENV_REGION) or environ.get(ENV_REGION_FALLBACK)


def read_vertex_settings(environ: Mapping[str, str] | None = None) -> VertexSettings:
    env = os.environ if environ is None else environ
    missing = [name for name in REQUIRED_ENV_VARS if not env.get(name)]
    if missing:
        raise ConfigError(f"missing required env var(s): {', '.join(missing)}")
    region = vertex_region(env)
    if not region:
        raise ConfigError(
            f"missing required env var: {ENV_REGION} (or fallback {ENV_REGION_FALLBACK})"
        )
    return VertexSettings(
        project_id=env[ENV_PROJECT_ID] or "",
        region=region,
        model=env[ENV_MODEL] or "",
        small_model=env[ENV_SMALL_MODEL] or "",
        base_url=env.get(ENV_BASE_URL),
        access_token=env.get(ENV_ACCESS_TOKEN),
    )


def _join_text_blocks(blocks: list[object]) -> str:
    parts = [block.text for block in blocks if isinstance(block, TextBlock)]
    return "".join(parts)


def build_vertex_chat(settings: VertexSettings) -> ChatFn:
    """Build a ChatFn backed by the AnthropicVertex SDK client."""
    client = AnthropicVertex(
        project_id=settings.project_id,
        region=settings.region,
        base_url=settings.base_url,
        access_token=settings.access_token,
    )

    def chat(system: str, user: str, model: str, max_tokens: int) -> str:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return _join_text_blocks(list(message.content))

    return chat


class VertexAIClient:
    """AIClient implementation on top of a ChatFn (unit-testable without network).

    Large-model calls (ANTHROPIC_MODEL): expert notes, report generation.
    Small-fast-model calls (ANTHROPIC_SMALL_FAST_MODEL): lens proposals,
    tone samples, critiques.
    """

    def __init__(
        self,
        chat: ChatFn,
        model: str,
        small_model: str,
    ) -> None:
        self._chat = chat
        self._model = model
        self._small_model = small_model

    def propose_lenses(self, doc_path: str, doc_content: str) -> list[LensDraft]:
        system, user = prompts.lens_proposal_prompt(doc_path, doc_content)
        raw = self._chat(system, user, self._small_model, MAX_TOKENS_LENSES)
        return parse_lenses(raw)

    def expert_notes(
        self, doc_path: str, doc_content: str, lens_title: str
    ) -> list[ExpertNoteDraft]:
        system, user = prompts.expert_note_prompt(doc_path, doc_content, lens_title)
        raw = self._chat(system, user, self._model, MAX_TOKENS_EXPERT)
        return parse_expert_notes(raw)

    def generate_report(self, dump_text: str) -> list[ParagraphDraft]:
        system, user = prompts.report_prompt(dump_text)
        raw = self._chat(system, user, self._model, MAX_TOKENS_REPORT)
        return parse_report(raw)

    def tone_samples(self, block: str, report_context: str) -> list[ToneSampleDraft]:
        system, user = prompts.tone_samples_prompt(block, report_context)
        raw = self._chat(system, user, self._small_model, MAX_TOKENS_TONE)
        return parse_tone_samples(raw)

    def critique(self, block: str, report_context: str) -> str:
        system, user = prompts.critique_prompt(block, report_context)
        raw = self._chat(system, user, self._small_model, MAX_TOKENS_CRITIQUE)
        return parse_critique(raw)


def build_ai_client(environ: Mapping[str, str] | None = None) -> AIClient:
    settings = read_vertex_settings(environ)
    return VertexAIClient(build_vertex_chat(settings), settings.model, settings.small_model)
