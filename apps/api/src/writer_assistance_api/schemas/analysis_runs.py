from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from writer_assistance_api.schemas.annotations import AnnotationResponse, QuoteAnchor

LensDiscoveryState = Literal["queued", "running", "succeeded", "failed", "cancelled"]
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


class DiscoveredLensResponse(BaseModel):
    name: str
    description: str


class AnalysisSuggestionResponse(BaseModel):
    id: str
    analysis_run_id: str
    lens: str
    body: str
    review_state: SuggestionReviewState
    created_at: datetime
    updated_at: datetime
    anchor: QuoteAnchor


class AnalysisLensResultResponse(BaseModel):
    id: str
    lens: str
    generation_state: AnalysisLensGenerationState
    error_message: str | None
    suggestions: list[AnalysisSuggestionResponse]


class AnalysisRunDetailResponse(BaseModel):
    id: str
    project_id: str
    resource_id: str
    lens_discovery_status: LensDiscoveryState
    discovered_lenses: list[DiscoveredLensResponse]
    generation_state: AnalysisRunGenerationState
    error_summary: str | None
    lens_results: list[AnalysisLensResultResponse]
    created_at: datetime
    updated_at: datetime


class SuggestionEnvelope(BaseModel):
    suggestion: AnalysisSuggestionResponse


class AcceptAnalysisSuggestionResponse(BaseModel):
    suggestion: AnalysisSuggestionResponse
    annotation: AnnotationResponse
