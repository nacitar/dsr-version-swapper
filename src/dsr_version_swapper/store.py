from __future__ import annotations

import hashlib
import os
import shutil
from importlib.metadata import distribution
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import SwapperError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .versions import VersionData

XDG_DATA_ROOT = (
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    / distribution(__package__.split(".")[0]).metadata["Name"]
)

_CHUNK_SIZE = 1 << 20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


class BlobStore:
    """Game files kept by the sha256 of their contents, each stored once."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, digest: str) -> Path:
        return self.root / digest

    def has(self, digest: str) -> bool:
        return self.path(digest).is_file()

    def add(self, source: Path, digest: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        partial = self.root / f"{digest}.partial"
        shutil.copyfile(source, partial)
        partial.replace(self.path(digest))

    def incomplete(self, data: VersionData, names: Iterable[str]) -> list[str]:
        """Which of the given versions are missing stored files."""
        return [
            name
            for name in names
            if any(
                digest is not None and not self.has(digest)
                for digest in data.files[name].values()
            )
        ]

    def require(self, data: VersionData, names: Iterable[str]) -> None:
        missing = self.incomplete(data, names)
        if missing:
            msg = (
                f"the local store ({self.root}) is missing files for "
                f"{', '.join(missing)}; run `dsr-version-swapper fetch "
                "--user <steam account>` first"
            )
            raise SwapperError(msg)


def default_store() -> BlobStore:
    return BlobStore(XDG_DATA_ROOT / "blobs")
