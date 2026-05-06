from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ResolutionStatus = Literal["exact", "fuzzy", "unresolved"]


class QuoteAnchor(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    quote_text: str = Field(alias="quoteText", min_length=1)
    normalized_text: str = Field(alias="normalizedText", min_length=1)
    start_offset: int = Field(alias="startOffset", ge=0)
    end_offset: int = Field(alias="endOffset", ge=0)
    block_path: list[str] = Field(alias="blockPath", min_length=1)
    resolution_status: ResolutionStatus = Field(alias="resolutionStatus")


class CreateAnnotationRequest(BaseModel):
    resource_id: str
    body: str = Field(min_length=1)
    anchor: QuoteAnchor


class AnnotationResponse(BaseModel):
    id: str
    project_id: str
    resource_id: str
    body: str
    origin_type: str
    provenance_source_id: str | None
    created_at: datetime
    updated_at: datetime
    anchor: QuoteAnchor
