from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dsr_version_swapper.errors import SwapperError
from dsr_version_swapper.store import BlobStore
from dsr_version_swapper.switch import detect, export, switch
from dsr_version_swapper.versions import EXE_FILE

from .fakes import CONTENTS, fill_store, make_data, write_version

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
    (game / "untouched.txt").write_text("keep me")
    return game


def test_detect(game: Path) -> None:
    assert detect(game, make_data()) == ["1.2.0.0"]
    write_version(game, "1.0.0.0")
    assert detect(game, make_data()) == ["1.0.0.0"]


def test_detect_unknown_state(game: Path) -> None:
    (game / "data" / "a.bin").write_bytes(b"modified")
    assert detect(game, make_data()) == []


def test_switch_every_direction(game: Path, store: BlobStore) -> None:
    data = make_data()
    for target in ["1.0.0.0", "1.1.0.0", "1.2.0.0", "1.1.0.0", "1.0.0.0"]:
        switch(game, data, store, target)
        assert detect(game, data) == [target]
        for path, content in CONTENTS[target].items():
            if content is None:
                assert not (game / path).exists()
            else:
                assert (game / path).read_bytes() == content
    assert (game / "untouched.txt").read_text() == "keep me"


def test_switch_reports_previous_and_changes(
    game: Path, store: BlobStore
) -> None:
    data = make_data()
    previous, changed = switch(game, data, store, "1.0.0.0")
    assert previous == ["1.2.0.0"]
    assert changed == 4
    assert switch(game, data, store, "1.0.0.0") == (["1.0.0.0"], 0)


def test_switch_leaves_no_temporary_files(
    game: Path, store: BlobStore
) -> None:
    switch(game, make_data(), store, "1.0.0.0")
    assert not list(game.rglob("*.dsr-tmp"))


def test_switch_refuses_unknown_state_unless_forced(
    game: Path, store: BlobStore
) -> None:
    data = make_data()
    (game / "data" / "a.bin").write_bytes(b"modified")
    with pytest.raises(SwapperError, match="match no known version"):
        switch(game, data, store, "1.0.0.0")
    assert (game / "data" / "a.bin").read_bytes() == b"modified"
    previous, _ = switch(game, data, store, "1.0.0.0", force=True)
    assert previous == []
    assert detect(game, data) == ["1.0.0.0"]


def test_switch_needs_the_store(game: Path, tmp_path: Path) -> None:
    empty = BlobStore(tmp_path / "empty")
    with pytest.raises(SwapperError, match="fetch"):
        switch(game, make_data(), empty, "1.0.0.0")
    assert detect(game, make_data()) == ["1.2.0.0"]


def test_export_writes_each_executable(
    tmp_path: Path, store: BlobStore
) -> None:
    data = make_data()
    written = export(data, store, ["1.0.0.0", "1.2.0.0"], tmp_path / "out")
    assert written == [
        tmp_path / "out" / "1.0.0.0" / EXE_FILE,
        tmp_path / "out" / "1.2.0.0" / EXE_FILE,
    ]
    assert written[0].read_bytes() == b"exe-1"
    assert written[1].read_bytes() == b"exe-3"
