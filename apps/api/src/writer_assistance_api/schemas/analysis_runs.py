from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from writer_assistance_api.ai.client import LensName
from writer_assistance_api.schemas.annotations import AnnotationResponse, QuoteAnchor

AnalysisRunGenerationState = Literal[
    "queued",
    "running",
    "succeeded",
    "completed_with_failures",
    "failed",
    "cancelled",
]
AnalysisLensGenerationState = Literal["queued", "running", "succeeded", "failed", "cancelled"]
SuggestionReviewState = Literal["unreviewed", "accepted", "discarded"]


class CreateAnalysisRunRequest(BaseModel):
    resource_id: str
    lenses: list[LensName] = Field(min_length=1)

    @field_validator("lenses")
    @classmethod
    def validate_unique_lenses(cls, value: list[LensName]) -> list[LensName]:
        seen: set[LensName] = set()
        unique_lenses: list[LensName] = []
        for lens in value:
            if lens in seen:
                continue
            seen.add(lens)
            unique_lenses.append(lens)
        if not unique_lenses:
            raise ValueError("At least one lens is required")
        return unique_lenses


class AnalysisSuggestionResponse(BaseModel):
    id: str
    analysis_run_id: str
    lens: LensName
    body: str
    review_state: SuggestionReviewState
    created_at: datetime
    updated_at: datetime
    anchor: QuoteAnchor


class AnalysisLensResultResponse(BaseModel):
    id: str
    lens: LensName
    generation_state: AnalysisLensGenerationState
    error_message: str | None
    suggestions: list[AnalysisSuggestionResponse]


class AnalysisRunDetailResponse(BaseModel):
    id: str
    project_id: str
    resource_id: str
    generation_state: AnalysisRunGenerationState
    lens_results: list[AnalysisLensResultResponse]
    created_at: datetime
    updated_at: datetime


class SuggestionEnvelope(BaseModel):
    suggestion: AnalysisSuggestionResponse


class AcceptAnalysisSuggestionResponse(BaseModel):
    suggestion: AnalysisSuggestionResponse
    annotation: AnnotationResponse
