from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from dsr_version_swapper.application import main
from dsr_version_swapper.store import BlobStore
from dsr_version_swapper.versions import EXE_FILE, load_version_data

from .fakes import fill_store, make_data, write_version

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(tmp_path: Path) -> BlobStore:
    store = BlobStore(tmp_path / "data" / "blobs")
    fill_store(store)
    return store


@pytest.fixture
def game(tmp_path: Path) -> Path:
    game = tmp_path / "game"
    write_version(game, "1.2.0.0")
    return game


def _run(
    game: Path, store: BlobStore, *arguments: str, running: bool = False
) -> int:
    return main(
        ["--game-dir", str(game), *arguments],
        data=make_data(),
        store=store,
        game_running=lambda: running,
    )


def test_list_marks_the_installed_version(
    game: Path, store: BlobStore, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(game, store, "list") == 0
    lines = capsys.readouterr().out.splitlines()
    assert "   1.0.0.0   date of 1.0.0.0" in lines
    assert " * 1.2.0.0   date of 1.2.0.0" in lines


def test_status_says_when_nothing_matches(
    tmp_path: Path, store: BlobStore, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "empty").mkdir()
    assert _run(tmp_path / "empty", store, "status") == 0
    output = capsys.readouterr().out
    assert "no known version" in output
    assert "1.1.0.0" in output


def test_list_with_the_real_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--game-dir", str(tmp_path), "list"]) == 0
    output = capsys.readouterr().out
    for name in load_version_data().names:
        assert name in output


def test_switch_and_back(
    game: Path, store: BlobStore, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(game, store, "switch", "1.0.0.0") == 0
    assert "1.2.0.0 -> 1.0.0.0" in capsys.readouterr().out
    assert (game / EXE_FILE).read_bytes() == b"exe-1"
    assert _run(game, store, "switch", "1.0.0.0") == 0
    assert "already 1.0.0.0" in capsys.readouterr().out
    assert _run(game, store, "switch", "1.2.0.0") == 0
    assert (game / EXE_FILE).read_bytes() == b"exe-3"


def test_unknown_version_lists_the_choices(
    game: Path, store: BlobStore, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        _run(game, store, "switch", "9.9.9")
    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert "invalid choice" in error
    assert "1.0.0.0" in error
    assert "1.2.0.0" in error


def test_switch_refuses_while_the_game_runs(
    game: Path, store: BlobStore, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(game, store, "switch", "1.0.0.0", running=True) == 1
    assert "close the game" in capsys.readouterr().err
    assert (game / EXE_FILE).read_bytes() == b"exe-3"
    arguments = ["switch", "1.0.0.0", "--ignore-running"]
    assert _run(game, store, *arguments, running=True) == 0
    assert (game / EXE_FILE).read_bytes() == b"exe-1"


def test_switch_without_the_store_points_at_fetch(
    game: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(game, BlobStore(tmp_path / "none"), "switch", "1.0.0.0") == 1
    assert "fetch" in capsys.readouterr().err


def test_export(
    game: Path,
    store: BlobStore,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        _run(game, store, "export", "1.0.0.0", "--to", str(tmp_path / "x"))
        == 0
    )
    assert (
        str(tmp_path / "x" / "1.0.0.0" / EXE_FILE) in capsys.readouterr().out
    )
    assert _run(game, store, "export") == 0
    assert (store.root.parent / "binaries" / "1.1.0.0" / EXE_FILE).is_file()


def test_export_unknown_version(
    game: Path, store: BlobStore, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(game, store, "export", "0.0") == 1
    error = capsys.readouterr().err
    assert "unknown version" in error
    assert "1.2.0.0" in error


def test_fetch_needs_depotdownloader(
    game: Path,
    store: BlobStore,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert _run(game, store, "fetch", "--user", "me") == 1
    assert "depotdownloader" in capsys.readouterr().err


def test_missing_game_folder(
    tmp_path: Path, store: BlobStore, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path / "nowhere", store, "status") == 1
    assert "--game-dir" in capsys.readouterr().err
