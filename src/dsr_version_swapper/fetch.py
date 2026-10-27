from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import SwapperError
from .store import sha256_file
from .versions import EXE_FILE

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from .store import BlobStore
    from .versions import Version, VersionData

DEPOTDOWNLOADER = "depotdownloader"

type Runner = Callable[[Sequence[str]], None]


def run_depotdownloader(command: Sequence[str]) -> None:
    try:
        subprocess.run(command, check=True)  # noqa: S603
    except (OSError, subprocess.CalledProcessError) as error:
        msg = f"{DEPOTDOWNLOADER} failed: {error}"
        raise SwapperError(msg) from error


@dataclass(frozen=True, kw_only=True)
class _Download:
    depot: int
    manifest: str
    paths: list[str]


@dataclass(frozen=True, kw_only=True)
class _Fetcher:
    data: VersionData
    store: BlobStore
    user: str
    run: Runner

    def _downloads(
        self, version: Version, needed: dict[str, str]
    ) -> list[_Download]:
        """Split the needed files by the Steam depot that holds them."""
        exe = [path for path in needed if path == EXE_FILE]
        content = [path for path in needed if path != EXE_FILE]
        downloads: list[_Download] = []
        if exe:
            downloads.append(
                _Download(
                    depot=self.data.exe_depot,
                    manifest=version.exe_manifest,
                    paths=exe,
                )
            )
        if content:
            downloads.append(
                _Download(
                    depot=self.data.content_depot,
                    manifest=version.content_manifest,
                    paths=content,
                )
            )
        return downloads

    def _command(
        self, download: _Download, target: Path, listing: Path
    ) -> list[str]:
        return [
            DEPOTDOWNLOADER,
            "-app",
            str(self.data.app),
            "-depot",
            str(download.depot),
            "-manifest",
            download.manifest,
            "-os",
            "windows",
            "-username",
            self.user,
            "-remember-password",
            "-dir",
            str(target),
            "-filelist",
            str(listing),
        ]

    def _store_downloaded(
        self, version: Version, target: Path, needed: dict[str, str]
    ) -> None:
        for path, digest in needed.items():
            downloaded = target / path
            if not downloaded.is_file():
                msg = (
                    f"[{version.name}] expected file was not downloaded: "
                    f"{path}"
                )
                raise SwapperError(msg)
            if sha256_file(downloaded) != digest:
                msg = (
                    f"[{version.name}] {path} does not match its recorded "
                    "hash; not storing it"
                )
                raise SwapperError(msg)
            self.store.add(downloaded, digest)

    def fetch_version(self, version: Version, work_dir: Path) -> None:
        needed = {
            path: digest
            for path, digest in self.data.files[version.name].items()
            if digest is not None and not self.store.has(digest)
        }
        if not needed:
            print(f"[{version.name}] nothing to download")
            return
        shutil.rmtree(work_dir, ignore_errors=True)
        target = work_dir / "files"
        target.mkdir(parents=True)
        for download in self._downloads(version, needed):
            listing = work_dir / f"filelist-{download.depot}.txt"
            listing.write_text(
                "\n".join(download.paths) + "\n", encoding="utf-8"
            )
            print(
                f"[{version.name}] depot {download.depot}: "
                f"{len(download.paths)} file(s)"
            )
            self.run(self._command(download, target, listing))
        self._store_downloaded(version, target, needed)
        shutil.rmtree(work_dir)
        print(f"[{version.name}] stored {len(needed)} file(s)")


def fetch(
    data: VersionData,
    store: BlobStore,
    user: str,
    work_dir: Path,
    run: Runner = run_depotdownloader,
) -> None:
    """Download only the files the store lacks, checking each against its hash.

    The newest version goes first because most files are shared with the older
    ones, which then only need what differs.
    """
    store.root.mkdir(parents=True, exist_ok=True)
    fetcher = _Fetcher(data=data, store=store, user=user, run=run)
    for version in [data.newest, *data.versions[:-1]]:
        fetcher.fetch_version(version, work_dir / version.name)
