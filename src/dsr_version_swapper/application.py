from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .errors import SwapperError
from .fetch import DEPOTDOWNLOADER, fetch
from .game import find_game_dir, is_game_running
from .store import default_store
from .switch import detect, export, switch
from .versions import load_version_data

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from .store import BlobStore
    from .versions import VersionData

_DESCRIPTION = """\
Switch an installed Dark Souls Remastered between its Steam patch versions by
patching only the files that differ. Run `fetch` once to download those files
from Steam into a local store, then `switch` between versions as needed. Use
`switch` with the newest version to restore the current Steam build.
"""


@dataclass(frozen=True, kw_only=True)
class _Context:
    data: VersionData
    store: BlobStore
    game_running: Callable[[], bool]


def _build_parser(data: VersionData) -> argparse.ArgumentParser:
    names = ", ".join(data.names)
    parser = argparse.ArgumentParser(
        prog="dsr-version-swapper",
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        help="the game's install folder (default: found via Steam)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="show the versions you can choose")
    commands.add_parser(
        "status", help="show which version is installed, and the choices"
    )
    switch_parser = commands.add_parser(
        "switch", help="patch the installed game to a version"
    )
    switch_parser.add_argument(
        "version",
        choices=data.names,
        metavar="VERSION",
        help=f"one of: {names}",
    )
    switch_parser.add_argument(
        "--force",
        action="store_true",
        help="switch even if the installed files match no known version",
    )
    switch_parser.add_argument(
        "--ignore-running",
        action="store_true",
        help="do not refuse to switch while the game is running",
    )
    export_parser = commands.add_parser(
        "export", help="write each version's DarkSoulsRemastered.exe"
    )
    export_parser.add_argument(
        "versions",
        nargs="*",
        metavar="VERSION",
        help=f"versions to write (default: all of {names})",
    )
    export_parser.add_argument(
        "--to",
        type=Path,
        help="destination folder (default: next to the local store)",
    )
    fetch_parser = commands.add_parser(
        "fetch", help="download the needed files from Steam"
    )
    fetch_parser.add_argument(
        "--user", required=True, help="your Steam account name"
    )
    return parser


def _print_versions(
    data: VersionData, installed: Sequence[str] | None
) -> None:
    print("versions you can choose:")
    for version in data.versions:
        marker = "*" if installed and version.name in installed else " "
        print(f" {marker} {version.name}   {version.date}")
    if installed is not None:
        print(
            "(* = what the installed game matches)"
            if installed
            else "(the installed game matches none of these)"
        )


def _game_dir(args: argparse.Namespace) -> Path:
    game_dir: Path | None = args.game_dir or find_game_dir()
    if game_dir is None or not game_dir.is_dir():
        msg = "could not find the game folder; pass --game-dir"
        raise SwapperError(msg)
    return game_dir


def _command_list(args: argparse.Namespace, context: _Context) -> int:
    try:
        installed = detect(_game_dir(args), context.data)
    except SwapperError:
        installed = None
    _print_versions(context.data, installed)
    return 0


def _command_status(args: argparse.Namespace, context: _Context) -> int:
    installed = detect(_game_dir(args), context.data)
    print(
        "installed game matches:",
        " / ".join(installed) or "no known version (mixed or modified files)",
    )
    _print_versions(context.data, installed)
    return 0


def _command_switch(args: argparse.Namespace, context: _Context) -> int:
    game_dir = _game_dir(args)
    if context.game_running() and not args.ignore_running:
        msg = "DarkSoulsRemastered.exe is running; close the game first"
        raise SwapperError(msg)
    previous, changed = switch(
        game_dir, context.data, context.store, args.version, force=args.force
    )
    if changed == 0 and args.version in previous:
        print(f"already {args.version}")
    else:
        print(
            f"{' / '.join(previous) or 'unknown'} -> {args.version}: "
            f"{changed} file(s) changed; verified"
        )
    return 0


def _command_export(args: argparse.Namespace, context: _Context) -> int:
    unknown = [
        name for name in args.versions if name not in context.data.names
    ]
    if unknown:
        msg = (
            f"unknown version(s): {', '.join(unknown)}; choose from "
            f"{', '.join(context.data.names)}"
        )
        raise SwapperError(msg)
    destination = args.to or context.store.root.parent / "binaries"
    for path in export(
        context.data,
        context.store,
        args.versions or context.data.names,
        destination,
    ):
        print(path)
    return 0


def _command_fetch(args: argparse.Namespace, context: _Context) -> int:
    if shutil.which(DEPOTDOWNLOADER) is None:
        msg = f"{DEPOTDOWNLOADER} was not found on PATH; install it first"
        raise SwapperError(msg)
    fetch(
        context.data,
        context.store,
        args.user,
        context.store.root.parent / "download",
    )
    missing = context.store.incomplete(context.data, context.data.names)
    print(
        "store complete"
        if not missing
        else f"store is still missing files for {', '.join(missing)}"
    )
    return 0 if not missing else 1


_COMMANDS: dict[str, Callable[[argparse.Namespace, _Context], int]] = {
    "list": _command_list,
    "status": _command_status,
    "switch": _command_switch,
    "export": _command_export,
    "fetch": _command_fetch,
}


def main(
    argv: Sequence[str] | None = None,
    *,
    data: VersionData | None = None,
    store: BlobStore | None = None,
    game_running: Callable[[], bool] = is_game_running,
) -> int:
    data = data or load_version_data()
    args = _build_parser(data).parse_args(argv)
    context = _Context(
        data=data, store=store or default_store(), game_running=game_running
    )
    try:
        return _COMMANDS[args.command](args, context)
    except SwapperError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
