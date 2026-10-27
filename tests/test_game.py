from __future__ import annotations

from typing import TYPE_CHECKING

from dsr_version_swapper.game import (
    GAME_FOLDER,
    find_game_dir,
    is_game_running,
    library_folders,
)

if TYPE_CHECKING:
    from pathlib import Path


def _game(library: Path) -> Path:
    path = library / "steamapps" / "common" / GAME_FOLDER
    path.mkdir(parents=True)
    return path


def test_finds_the_game_in_the_main_library(tmp_path: Path) -> None:
    game = _game(tmp_path / "Steam")
    assert find_game_dir([tmp_path / "Steam"]) == game


def test_finds_the_game_in_another_library(tmp_path: Path) -> None:
    steam = tmp_path / "Steam"
    (steam / "steamapps").mkdir(parents=True)
    other = tmp_path / "games"
    game = _game(other)
    (steam / "steamapps" / "libraryfolders.vdf").write_text(
        f'"libraryfolders"\n{{\n  "0"\n  {{\n    "path"  "{steam}"\n  }}\n'
        f'  "1"\n  {{\n    "path"  "{other}"\n  }}\n}}\n',
        encoding="utf-8",
    )
    assert library_folders(steam) == [steam, other]
    assert find_game_dir([steam]) == game


def test_no_game_found(tmp_path: Path) -> None:
    assert find_game_dir([tmp_path / "nothing"]) is None
    assert library_folders(tmp_path / "nothing") == []


def test_is_game_running(tmp_path: Path) -> None:
    proc = tmp_path / "proc"
    (proc / "self").mkdir(parents=True)
    (proc / "100").mkdir()
    (proc / "100" / "cmdline").write_bytes(b"python\0script.py\0")
    (proc / "200").mkdir()  # no readable cmdline
    assert not is_game_running(proc)
    (proc / "300").mkdir()
    (proc / "300" / "cmdline").write_bytes(
        b"Z:\\steam\\DarkSoulsRemastered.exe\0"
    )
    assert is_game_running(proc)
