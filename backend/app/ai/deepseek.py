"""Live DeepSeek backend behind the AIClient contract (R-070, DEC-024/DEC-025).

OpenAI-compatible chat-completions transport at api.deepseek.com. Env vars per
R-072/DEC-026: DEEPSEEK_API_KEY (required at build time; missing -> ConfigError,
R-074) and DEEPSEEK_MODEL (optional; falls back to DEFAULT_MODEL — R-073). Both
the large and the small-fast call classes route to the single configured model
id until a second DeepSeek model exists (SD-21).

The httpx client is never imported by other modules; this module owns the
transport so the rest of the app (and all default tests) stays offline.
"""

import os
from collections.abc import Mapping

import httpx

from app.ai import prompts
from app.ai.client import (
    MAX_TOKENS_CRITIQUE,
    MAX_TOKENS_EXPERT,
    MAX_TOKENS_LENSES,
    MAX_TOKENS_REPORT,
    MAX_TOKENS_TONE,
    AIClient,
    ChatFn,
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
from app.errors import AIError, ConfigError

BASE_URL = "https://api.deepseek.com"
CHAT_COMPLETIONS_PATH = "/chat/completions"
ENV_API_KEY = "DEEPSEEK_API_KEY"
ENV_MODEL = "DEEPSEEK_MODEL"
DEFAULT_MODEL = "deepseek-v4-flash"

REQUIRED_ENV_VARS = (ENV_API_KEY,)

REQUEST_TIMEOUT_SECONDS = 120.0


class DeepSeekSettings:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model


def read_deepseek_settings(environ: Mapping[str, str] | None = None) -> DeepSeekSettings:
    env = os.environ if environ is None else environ
    missing = [name for name in REQUIRED_ENV_VARS if not env.get(name)]
    if missing:
        raise ConfigError(f"missing required env var(s): {', '.join(missing)}")
    return DeepSeekSettings(
        api_key=env[ENV_API_KEY] or "",
        model=env.get(ENV_MODEL) or DEFAULT_MODEL,
    )


def _assistant_text(payload: object) -> str:
    """choices[0].message.content from the OpenAI-compatible envelope (strict)."""
    if not isinstance(payload, dict):
        raise AIError("deepseek API response is not a JSON object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIError("deepseek API response has no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise AIError("deepseek API response choice is not a JSON object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise AIError("deepseek API response choice has no message object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AIError("deepseek API response has no assistant text")
    return content.strip()


def build_deepseek_chat(settings: DeepSeekSettings) -> ChatFn:
    """Build a ChatFn backed by a plain httpx client (OpenAI-compatible)."""
    client = httpx.Client(
        base_url=BASE_URL,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )

    def chat(system: str, user: str, model: str, max_tokens: int) -> str:
        try:
            response = client.post(
                CHAT_COMPLETIONS_PATH,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "stream": False,
                },
            )
        except httpx.HTTPError as exc:
            raise AIError(f"deepseek API request failed: {str(exc)[:500]}") from exc
        if response.status_code != 200:
            raise AIError(f"deepseek API error {response.status_code}: {response.text[:500]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AIError(
                f"deepseek API response is not valid JSON: {response.text[:500]}"
            ) from exc
        return _assistant_text(payload)

    return chat


class DeepSeekAIClient:
    """AIClient implementation on top of a ChatFn (unit-testable without network).

    Every call kind uses the single configured DeepSeek model id (SD-21) and the
    shared per-kind token budgets from the AI boundary module.
    """

    def __init__(self, chat: ChatFn, model: str) -> None:
        self._chat = chat
        self._model = model

    def propose_lenses(self, doc_path: str, doc_content: str) -> list[LensDraft]:
        system, user = prompts.lens_proposal_prompt(doc_path, doc_content)
        raw = self._chat(system, user, self._model, MAX_TOKENS_LENSES)
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
        raw = self._chat(system, user, self._model, MAX_TOKENS_TONE)
        return parse_tone_samples(raw)

    def critique(self, block: str, report_context: str) -> str:
        system, user = prompts.critique_prompt(block, report_context)
        raw = self._chat(system, user, self._model, MAX_TOKENS_CRITIQUE)
        return parse_critique(raw)


def build_ai_client(environ: Mapping[str, str] | None = None) -> AIClient:
    settings = read_deepseek_settings(environ)
    return DeepSeekAIClient(build_deepseek_chat(settings), settings.model)
