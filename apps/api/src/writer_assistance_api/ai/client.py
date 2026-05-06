from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from writer_assistance_api.schemas.annotations import QuoteAnchor

LensName = Literal["financial", "real_estate", "political", "software_engineering"]
LENS_CATALOG: tuple[LensName, ...] = (
    "financial",
    "real_estate",
    "political",
    "software_engineering",
)


class AiSuggestionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    anchor: QuoteAnchor


AiSuggestionDraftLike: TypeAlias = AiSuggestionDraft | Mapping[str, Any]


class AiClient(Protocol):
    def analyze_resource(
        self,
        *,
        lens: LensName,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        ...


def normalize_suggestion_drafts(
    suggestions: Sequence[AiSuggestionDraftLike],
) -> list[AiSuggestionDraft]:
    normalized: list[AiSuggestionDraft] = []
    for suggestion in suggestions:
        if isinstance(suggestion, AiSuggestionDraft):
            normalized.append(suggestion)
            continue
        normalized.append(AiSuggestionDraft.model_validate(suggestion))
    return normalized
