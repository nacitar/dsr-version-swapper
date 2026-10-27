"""Small made-up versions and a stand-in for depotdownloader."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dsr_version_swapper.versions import EXE_FILE, Version, VersionData

if TYPE_CHECKING:
    from collections.abc import Sequence

    from dsr_version_swapper.store import BlobStore

EXE_DEPOT = 2
CONTENT_DEPOT = 1

# version -> path -> contents (None: the version does not have the file).
# data/a.bin is shared by the last two versions and data/b.bin by the first
# two; extra.bin exists only in the newest.
CONTENTS: dict[str, dict[str, bytes | None]] = {
    "1.0.0.0": {
        EXE_FILE: b"exe-1",
        "data/a.bin": b"a-1",
        "data/b.bin": b"b-1",
        "extra.bin": None,
    },
    "1.1.0.0": {
        EXE_FILE: b"exe-2",
        "data/a.bin": b"a-2",
        "data/b.bin": b"b-1",
        "extra.bin": None,
    },
    "1.2.0.0": {
        EXE_FILE: b"exe-3",
        "data/a.bin": b"a-2",
        "data/b.bin": None,
        "extra.bin": b"e-3",
    },
}


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def make_data() -> VersionData:
    versions = tuple(
        Version(
            name=name,
            date=f"date of {name}",
            content_manifest=f"content-{name}",
            exe_manifest=f"exe-{name}",
        )
        for name in CONTENTS
    )
    return VersionData(
        app=1,
        content_depot=CONTENT_DEPOT,
        exe_depot=EXE_DEPOT,
        versions=versions,
        files={
            name: {
                path: None if content is None else sha(content)
                for path, content in files.items()
            }
            for name, files in CONTENTS.items()
        },
    )


def write_version(root: Path, name: str) -> None:
    """Make a game folder hold exactly the given version's tracked files."""
    for path, content in CONTENTS[name].items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(content)


def fill_store(store: BlobStore) -> None:
    for files in CONTENTS.values():
        for content in files.values():
            if content is not None and not store.has(sha(content)):
                source = store.root.parent / "source"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(content)
                store.add(source, sha(content))


@dataclass
class FakeSteam:
    """Stands in for depotdownloader, serving the made-up versions."""

    data: VersionData
    calls: list[tuple[int, str, list[str]]] = field(default_factory=list)
    tampered: set[str] = field(default_factory=set)
    omitted: set[str] = field(default_factory=set)

    def __call__(self, command: Sequence[str]) -> None:
        options: dict[str, str] = {}
        index = 1
        while index < len(command):
            if command[index] == "-remember-password":
                index += 1
            else:
                options[command[index]] = command[index + 1]
                index += 2
        depot = int(options["-depot"])
        manifest = options["-manifest"]
        paths = Path(options["-filelist"]).read_text(encoding="utf-8").split()
        self.calls.append((depot, manifest, paths))
        assert options["-os"] == "windows"
        version = next(
            version.name
            for version in self.data.versions
            if manifest
            == (
                version.exe_manifest
                if depot == EXE_DEPOT
                else version.content_manifest
            )
        )
        for path in paths:
            if (path == EXE_FILE) != (depot == EXE_DEPOT):
                continue  # the file is not in this depot
            content = CONTENTS[version][path]
            assert content is not None
            if path in self.omitted:
                continue
            if path in self.tampered:
                content += b"!"
            target = Path(options["-dir"]) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
