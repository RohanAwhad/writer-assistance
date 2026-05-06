from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class StoredObject(BaseModel):
    storage_path: str
    content_hash: str


class StorageDriver(Protocol):
    def prepare_object(self, *, project_id: str, logical_path: str, content: bytes) -> StoredObject: ...

    def put_object(
        self,
        *,
        project_id: str,
        logical_path: str,
        content: bytes,
        stored_object: StoredObject | None = None,
    ) -> StoredObject: ...

    def read_object(self, storage_path: str) -> bytes: ...

    def delete_object(self, storage_path: str) -> None: ...
