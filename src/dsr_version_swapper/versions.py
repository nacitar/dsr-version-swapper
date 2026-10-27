from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources

EXE_FILE = "DarkSoulsRemastered.exe"


@dataclass(frozen=True, kw_only=True)
class Version:
    name: str
    date: str
    content_manifest: str
    exe_manifest: str


@dataclass(frozen=True, kw_only=True)
class VersionData:
    """What is known about each version; contains no game data.

    `files` maps each version to every path that differs between any two
    versions, with the sha256 of that file in the version (None when the
    version does not have the file).
    """

    app: int
    content_depot: int
    exe_depot: int
    versions: tuple[Version, ...]  # oldest first
    files: dict[str, dict[str, str | None]]

    @property
    def names(self) -> list[str]:
        return [version.name for version in self.versions]

    @property
    def newest(self) -> Version:
        return self.versions[-1]

    @property
    def paths(self) -> list[str]:
        return sorted(self.files[self.newest.name])


def load_version_data() -> VersionData:
    text = (
        resources.files(__package__)
        .joinpath("data", "dsr_versions.json")
        .read_text(encoding="utf-8")
    )
    raw = json.loads(text)
    data = VersionData(
        app=raw["app"],
        content_depot=raw["depots"]["content"],
        exe_depot=raw["depots"]["exe"],
        versions=tuple(
            Version(
                name=name,
                date=entry["date"],
                content_manifest=entry["content_manifest"],
                exe_manifest=entry["exe_manifest"],
            )
            for name, entry in raw["versions"].items()
        ),
        files=raw["files"],
    )
    path_sets = {frozenset(paths) for paths in data.files.values()}
    if len(path_sets) != 1 or set(data.files) != set(data.names):
        msg = "inconsistent version data"
        raise ValueError(msg)
    return data
