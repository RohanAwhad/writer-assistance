from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from writer_assistance_api.storage import StorageDriver, StoredObject


class DiskStorage(StorageDriver):
    def __init__(self, root: Path) -> None:
        self.root = root

    def put_object(self, *, project_id: str, logical_path: str, content: bytes) -> StoredObject:
        target = self.root / project_id / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredObject(storage_path=str(target), content_hash=sha256(content).hexdigest())

    def read_object(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()
