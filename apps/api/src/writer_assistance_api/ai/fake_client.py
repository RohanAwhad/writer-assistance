from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from writer_assistance_api.ai.client import (
    AiSuggestionDraft,
    AiSuggestionDraftLike,
    DiscoveredLens,
    normalize_suggestion_drafts,
    resolve_analysis_lens,
)
from writer_assistance_api.schemas.annotations import QuoteAnchor

SMOKE_SUGGESTION_BODY = "Highlight the demand trend as evidence for pricing power."
SMOKE_DISCOVERED_LENSES = [
    DiscoveredLens(
        name="Demand trend",
        description="Highlights pricing power and revenue implications in the current resource.",
    )
]


class FakeAiClient:
    def __init__(
        self,
        *,
        discovered_lenses: Sequence[DiscoveredLens] | None = None,
        outcomes_by_lens: Mapping[str, Sequence[Sequence[AiSuggestionDraftLike] | Exception]] | None = None,
    ) -> None:
        self._discovered_lenses = list(discovered_lenses or [])
        self._outcomes_by_lens = {key: list(value) for key, value in (outcomes_by_lens or {}).items()}
        self.calls: list[dict[str, Any]] = []

    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]:
        self.calls.append(
            {
                "kind": "discover",
                "markdown": markdown,
                "logical_path": logical_path,
            }
        )
        return list(self._discovered_lenses)

    def analyze_resource(
        self,
        *,
        markdown: str,
        logical_path: str,
        lens_name: str | None = None,
        lens_description: str | None = None,
        lens: str | None = None,
    ) -> list[AiSuggestionDraft]:
        resolved_lens_name, resolved_lens_description = resolve_analysis_lens(
            lens_name=lens_name,
            lens_description=lens_description,
            lens=lens,
        )
        self.calls.append(
            {
                "kind": "analyze",
                "lens_name": resolved_lens_name,
                "lens_description": resolved_lens_description,
                "markdown": markdown,
                "logical_path": logical_path,
            }
        )
        outcomes = self._outcomes_by_lens.get(resolved_lens_name)
        if not outcomes:
            return []

        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return normalize_suggestion_drafts(outcome)


class SmokeAiClient:
    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]:
        del markdown, logical_path
        return list(SMOKE_DISCOVERED_LENSES)

    def analyze_resource(
        self,
        *,
        markdown: str,
        logical_path: str,
        lens_name: str | None = None,
        lens_description: str | None = None,
        lens: str | None = None,
    ) -> list[AiSuggestionDraft]:
        resolved_lens_name, _ = resolve_analysis_lens(
            lens_name=lens_name,
            lens_description=lens_description,
            lens=lens,
        )
        del logical_path
        if resolved_lens_name not in {"financial", SMOKE_DISCOVERED_LENSES[0].name}:
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
