from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from .errors import SwapperError
from .store import sha256_file
from .versions import EXE_FILE

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from .store import BlobStore
    from .versions import VersionData


def current_state(
    game_dir: Path, paths: Iterable[str]
) -> dict[str, str | None]:
    state: dict[str, str | None] = {}
    for relative in paths:
        path = game_dir / relative
        state[relative] = sha256_file(path) if path.is_file() else None
    return state


def detect(game_dir: Path, data: VersionData) -> list[str]:
    """The known versions the installed files match (normally one)."""
    state = current_state(game_dir, data.paths)
    return [name for name in data.names if data.files[name] == state]


def _apply(
    game_dir: Path, data: VersionData, store: BlobStore, target: str
) -> int:
    changed = 0
    for relative, digest in data.files[target].items():
        destination = game_dir / relative
        if digest is None:
            if destination.exists():
                destination.unlink()
                changed += 1
            continue
        if destination.is_file() and sha256_file(destination) == digest:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".dsr-tmp")
        shutil.copyfile(store.path(digest), temporary)
        temporary.replace(destination)
        changed += 1
    return changed


def switch(
    game_dir: Path,
    data: VersionData,
    store: BlobStore,
    target: str,
    *,
    force: bool = False,
) -> tuple[list[str], int]:
    """Patch the installed game to the target version.

    Returns the versions it matched before and how many files were changed.
    """
    installed = detect(game_dir, data)
    store.require(data, [target, *installed])
    if not installed and not force:
        msg = (
            "the installed files match no known version, so they will not be "
            "overwritten; run Steam's 'Verify integrity of game files' first, "
            "or pass --force"
        )
        raise SwapperError(msg)
    if target in installed:
        return installed, 0
    changed = _apply(game_dir, data, store, target)
    if target not in detect(game_dir, data):
        msg = "verification failed: the files do not match the target version"
        raise SwapperError(msg)
    return installed, changed


def export(
    data: VersionData,
    store: BlobStore,
    names: Iterable[str],
    destination: Path,
) -> list[Path]:
    """Write DarkSoulsRemastered.exe for each version under destination."""
    chosen = list(names)
    store.require(data, chosen)
    written: list[Path] = []
    for name in chosen:
        digest = data.files[name][EXE_FILE]
        if digest is None:
            continue
        target = destination / name / EXE_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(store.path(digest), target)
        written.append(target)
    return written
