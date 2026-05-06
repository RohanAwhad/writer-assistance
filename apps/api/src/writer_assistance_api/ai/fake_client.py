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
