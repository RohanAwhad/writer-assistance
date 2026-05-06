from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    logical_path: str
    original_filename: str
    content_hash: str
    upload_status: str
    created_at: datetime


class ResourceContentResponse(BaseModel):
    resource_id: str
    markdown: str
