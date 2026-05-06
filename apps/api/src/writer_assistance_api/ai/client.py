from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol, TypeAlias, overload

from pydantic import BaseModel, ConfigDict, Field

from writer_assistance_api.schemas.annotations import QuoteAnchor

LensName = Literal["financial", "real_estate", "political", "software_engineering"]
LENS_CATALOG: tuple[LensName, ...] = (
    "financial",
    "real_estate",
    "political",
    "software_engineering",
)
LEGACY_LENS_DESCRIPTIONS: Mapping[str, str] = {
    "financial": "Focus on financial signals, costs, pricing, demand, revenue implications, and investment relevance.",
    "real_estate": "Focus on land use, zoning, property value implications, occupancy, supply constraints, and development signals.",
    "political": "Focus on governance, regulation, public policy, institutional power, and political risk or opportunity.",
    "software_engineering": "Focus on systems design, implementation constraints, process trade-offs, reliability, and technical debt themes.",
}


class DiscoveredLens(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class AiSuggestionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    anchor: QuoteAnchor


AiSuggestionDraftLike: TypeAlias = AiSuggestionDraft | Mapping[str, Any]


class AiClient(Protocol):
    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]:
        ...

    @overload
    def analyze_resource(
        self,
        *,
        lens_name: str,
        lens_description: str,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        ...

    @overload
    def analyze_resource(
        self,
        *,
        lens: LensName,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        ...

    def analyze_resource(
        self,
        *,
        markdown: str,
        logical_path: str,
        lens_name: str | None = None,
        lens_description: str | None = None,
        lens: LensName | None = None,
    ) -> list[AiSuggestionDraft]:
        ...


def resolve_analysis_lens(
    *,
    lens_name: str | None = None,
    lens_description: str | None = None,
    lens: str | None = None,
) -> tuple[str, str]:
    if lens_name is not None or lens_description is not None:
        if lens_name is None or lens_description is None:
            raise TypeError("analyze_resource requires both lens_name and lens_description")
        resolved_name = lens_name.strip()
        resolved_description = lens_description.strip()
        if not resolved_name:
            raise ValueError("lens_name must not be blank")
        if not resolved_description:
            raise ValueError("lens_description must not be blank")
        return resolved_name, resolved_description

    if lens is None:
        raise TypeError("analyze_resource requires lens_name/lens_description or lens")

    resolved_lens = lens.strip()
    if not resolved_lens:
        raise ValueError("lens must not be blank")
    if resolved_lens not in LEGACY_LENS_DESCRIPTIONS:
        raise ValueError(f"Unknown legacy lens: {resolved_lens}")
    return resolved_lens, LEGACY_LENS_DESCRIPTIONS[resolved_lens]


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
