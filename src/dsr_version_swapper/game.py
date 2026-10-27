from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

GAME_FOLDER = "DARK SOULS REMASTERED"
_EXE_NAME = b"DarkSoulsRemastered.exe"
_LIBRARY_PATH = re.compile(r'"path"\s+"([^"]+)"')


def steam_roots() -> list[Path]:
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )
    return [data_home / "Steam", Path.home() / ".steam" / "steam"]


def library_folders(steam_root: Path) -> list[Path]:
    """Extra Steam library locations listed in libraryfolders.vdf."""
    listing = steam_root / "steamapps" / "libraryfolders.vdf"
    try:
        text = listing.read_text(encoding="utf-8")
    except OSError:
        return []
    return [
        Path(path.replace("\\\\", "\\"))
        for path in _LIBRARY_PATH.findall(text)
    ]


def find_game_dir(roots: Sequence[Path] | None = None) -> Path | None:
    for root in steam_roots() if roots is None else roots:
        for library in [root, *library_folders(root)]:
            candidate = library / "steamapps" / "common" / GAME_FOLDER
            if candidate.is_dir():
                return candidate
    return None


def is_game_running(proc: Path = Path("/proc")) -> bool:
    """True if any process's command line mentions the game executable."""
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command_line = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if _EXE_NAME in command_line:
            return True
    return False
