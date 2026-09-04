"""AI client contracts (R-004): the single boundary every AI call crosses.

Draft dataclasses are the parsed, typed outputs the rest of the app consumes.
``AIClient`` is the protocol implemented by the live provider backends
(AnthropicVertex, DeepSeek) and by test fakes; endpoints depend on it and are
therefore fully offline-testable (spec SD-16). ``ChatFn`` and the per-call-kind
token budgets are shared by every provider transport (SD-21).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

ChatFn = Callable[[str, str, str, int], str]
"""chat(system, user, model, max_tokens) -> assistant text; the transport seam."""

MAX_TOKENS_LENSES = 1024
MAX_TOKENS_EXPERT = 4096
MAX_TOKENS_REPORT = 8192
MAX_TOKENS_TONE = 2048
MAX_TOKENS_CRITIQUE = 2048


@dataclass(frozen=True)
class LensDraft:
    title: str
    rationale: str


@dataclass(frozen=True)
class ExpertNoteDraft:
    content: str


@dataclass(frozen=True)
class ToneSampleDraft:
    tone: str
    text: str


@dataclass(frozen=True)
class ParagraphDraft:
    text: str
    source_entry_ids: tuple[int, ...] = field(default_factory=tuple)


class AIClient(Protocol):
    def propose_lenses(self, doc_path: str, doc_content: str) -> list[LensDraft]: ...

    def expert_notes(
        self, doc_path: str, doc_content: str, lens_title: str
    ) -> list[ExpertNoteDraft]: ...

    def generate_report(self, dump_text: str) -> list[ParagraphDraft]: ...

    def tone_samples(self, block: str, report_context: str) -> list[ToneSampleDraft]: ...

    def critique(self, block: str, report_context: str) -> str: ...
