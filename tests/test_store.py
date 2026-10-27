from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dsr_version_swapper.errors import SwapperError
from dsr_version_swapper.store import BlobStore, sha256_file

from .fakes import fill_store, make_data

if TYPE_CHECKING:
    from pathlib import Path


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    assert sha256_file(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_add_and_has(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "blobs")
    source = tmp_path / "source"
    source.write_bytes(b"abc")
    digest = sha256_file(source)
    assert not store.has(digest)
    store.add(source, digest)
    assert store.has(digest)
    assert store.path(digest).read_bytes() == b"abc"
    assert not list(store.root.glob("*.partial"))


def test_require_names_what_is_missing(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "blobs")
    data = make_data()
    assert store.incomplete(data, data.names) == data.names
    with pytest.raises(SwapperError, match=r"1\.0\.0\.0.*fetch"):
        store.require(data, ["1.0.0.0"])
    fill_store(store)
    assert store.incomplete(data, data.names) == []
    store.require(data, data.names)
