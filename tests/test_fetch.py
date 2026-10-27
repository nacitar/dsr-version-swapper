from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dsr_version_swapper.errors import SwapperError
from dsr_version_swapper.fetch import fetch
from dsr_version_swapper.store import BlobStore
from dsr_version_swapper.versions import EXE_FILE

from .fakes import (
    CONTENT_DEPOT,
    CONTENTS,
    EXE_DEPOT,
    FakeSteam,
    make_data,
    sha,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(tmp_path: Path) -> BlobStore:
    return BlobStore(tmp_path / "data" / "blobs")


def test_fetch_fills_the_store(store: BlobStore, tmp_path: Path) -> None:
    data = make_data()
    steam = FakeSteam(data)
    fetch(data, store, "me", tmp_path / "work", steam)
    assert store.incomplete(data, data.names) == []
    wanted = {
        sha(content)
        for files in CONTENTS.values()
        for content in files.values()
        if content is not None
    }
    assert {path.name for path in store.root.iterdir()} == wanted


def test_fetch_asks_only_for_what_is_missing(
    store: BlobStore, tmp_path: Path
) -> None:
    data = make_data()
    steam = FakeSteam(data)
    fetch(data, store, "me", tmp_path / "work", steam)
    requested = [path for _, _, paths in steam.calls for path in paths]
    # The newest version is fetched in full first (3 files), then each older
    # one asks only for what is not already stored: 3 for the oldest, and just
    # the executable for the middle one.
    assert len(requested) == 3 + 3 + 1
    assert requested.count(EXE_FILE) == 3


def test_fetch_uses_the_right_depot_for_each_file(
    store: BlobStore, tmp_path: Path
) -> None:
    data = make_data()
    steam = FakeSteam(data)
    fetch(data, store, "me", tmp_path / "work", steam)
    for depot, _, paths in steam.calls:
        assert (depot == EXE_DEPOT) == (paths == [EXE_FILE])
        assert depot in {EXE_DEPOT, CONTENT_DEPOT}
    first = steam.calls[0]
    assert first[1] == f"exe-{data.newest.name}"


def test_fetch_cleans_up_and_is_repeatable(
    store: BlobStore, tmp_path: Path
) -> None:
    data = make_data()
    work = tmp_path / "work"
    fetch(data, store, "me", work, FakeSteam(data))
    assert not any(work.iterdir())
    steam = FakeSteam(data)
    fetch(data, store, "me", work, steam)
    assert steam.calls == []


def test_fetch_rejects_a_file_that_fails_its_hash(
    store: BlobStore, tmp_path: Path
) -> None:
    data = make_data()
    steam = FakeSteam(data, tampered={"data/a.bin"})
    with pytest.raises(SwapperError, match=r"data/a\.bin.*hash"):
        fetch(data, store, "me", tmp_path / "work", steam)
    assert store.incomplete(data, [data.newest.name]) != []


def test_fetch_reports_a_file_that_was_not_downloaded(
    store: BlobStore, tmp_path: Path
) -> None:
    data = make_data()
    steam = FakeSteam(data, omitted={"extra.bin"})
    with pytest.raises(SwapperError, match=r"not downloaded.*extra\.bin"):
        fetch(data, store, "me", tmp_path / "work", steam)
