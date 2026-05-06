from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
from uuid import uuid4

from writer_assistance_api.storage import StorageDriver, StoredObject


class DiskStorage(StorageDriver):
    def __init__(self, root: Path) -> None:
        self.root = root

    def prepare_object(self, *, project_id: str, logical_path: str, content: bytes) -> StoredObject:
        target = self.root / project_id / ".objects" / str(uuid4()) / Path(*PurePosixPath(logical_path).parts)
        return StoredObject(storage_path=str(target), content_hash=sha256(content).hexdigest())

    def put_object(
        self,
        *,
        project_id: str,
        logical_path: str,
        content: bytes,
        stored_object: StoredObject | None = None,
    ) -> StoredObject:
        prepared_object = stored_object or self.prepare_object(
            project_id=project_id,
            logical_path=logical_path,
            content=content,
        )
        target = Path(prepared_object.storage_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(content)
            return prepared_object
        except Exception:
            self.delete_object(prepared_object.storage_path)
            raise

    def read_object(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def delete_object(self, storage_path: str) -> None:
        Path(storage_path).unlink(missing_ok=True)
