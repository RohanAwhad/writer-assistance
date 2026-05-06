from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from writer_assistance_api.ai.client import (
    LENS_CATALOG,
    AiSuggestionDraft,
    AiSuggestionDraftLike,
    LensName,
    normalize_suggestion_drafts,
)
from writer_assistance_api.schemas.annotations import QuoteAnchor

SMOKE_SUGGESTION_BODY = "Highlight the demand trend as evidence for pricing power."


class FakeAiClient:
    def __init__(
        self,
        outcomes_by_lens: Mapping[LensName, Sequence[Sequence[AiSuggestionDraftLike] | Exception]] | None = None,
    ) -> None:
        self._outcomes_by_lens = {
            lens: list(outcomes_by_lens.get(lens, [])) for lens in LENS_CATALOG
        } if outcomes_by_lens is not None else {lens: [] for lens in LENS_CATALOG}
        self.calls: list[dict[str, Any]] = []

    def analyze_resource(
        self,
        *,
        lens: LensName,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        self.calls.append(
            {
                "lens": lens,
                "markdown": markdown,
                "logical_path": logical_path,
            }
        )
        outcomes = self._outcomes_by_lens.get(lens)
        if not outcomes:
            return []

        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return normalize_suggestion_drafts(outcome)


class SmokeAiClient:
    def analyze_resource(
        self,
        *,
        lens: LensName,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        del logical_path
        if lens != "financial":
            return []

        paragraph = _first_non_heading_paragraph(markdown)
        return [
            AiSuggestionDraft(
                body=SMOKE_SUGGESTION_BODY,
                anchor=QuoteAnchor(
                    quoteText=paragraph,
                    normalizedText=" ".join(paragraph.split()).lower(),
                    startOffset=0,
                    endOffset=len(paragraph),
                    blockPath=["paragraph", "1"],
                    resolutionStatus="exact",
                ),
            )
        ]


def _first_non_heading_paragraph(markdown: str) -> str:
    for line in markdown.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        return candidate
    raise ValueError("Smoke AI mode requires markdown with at least one paragraph")
