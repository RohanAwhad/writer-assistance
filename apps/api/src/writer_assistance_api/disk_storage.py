from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
from uuid import uuid4

from writer_assistance_api.storage import StorageDriver, StoredObject


class DiskStorage(StorageDriver):
    def __init__(self, root: Path) -> None:
        self.root = root

    def put_object(self, *, project_id: str, logical_path: str, content: bytes) -> StoredObject:
        target = self.root / project_id / ".objects" / str(uuid4()) / Path(*PurePosixPath(logical_path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(content)
            return StoredObject(storage_path=str(target), content_hash=sha256(content).hexdigest())
        except Exception:
            self.delete_object(str(target))
            raise

    def read_object(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def delete_object(self, storage_path: str) -> None:
        Path(storage_path).unlink(missing_ok=True)
