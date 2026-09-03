"""AI client contracts (R-004): the single boundary every AI call crosses.

Draft dataclasses are the parsed, typed outputs the rest of the app consumes.
``AIClient`` is the protocol implemented by the live AnthropicVertex-backed
wrapper and by test fakes; endpoints depend on it and are therefore fully
offline-testable (spec SD-16).
"""

from dataclasses import dataclass, field
from typing import Protocol


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
