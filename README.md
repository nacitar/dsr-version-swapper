# DSR Version Swapper

Switches an installed **Dark Souls: Remastered** (Steam) between its patch
versions, and back, by patching only the files that differ. Useful for
testing tools and mods against older builds without keeping a full copy of the
game for each one.

Only 33 files differ across all five known versions (about 320 MB in total),
so the tool downloads just those, once, and keeps them in a small local store.
Switching then copies a handful of files into your install.

| Version | Steam release |
|---|---|
| 1.0.1.0 | 23 May 2018 (release) |
| 1.0.1.1 | 28 May 2018 |
| 1.0.1.2 | 8 Jun 2018 |
| 1.0.3.0 | 11 Jul 2018 |
| 1.0.3.1 | 9 Nov 2022 (the current Steam build) |

This tool contains **no game files**. Everything it stores comes from Steam,
downloaded with your own account, which must own the game. It is not
affiliated with or endorsed by FromSoftware, Bandai Namco, or Valve.

## Requirements

- Linux with a Steam install of Dark Souls: Remastered.
- Python 3.12 or newer.
- [`depotdownloader`](https://github.com/SteamRE/DepotDownloader) on your
  `PATH`, for the one-time `fetch` step. It is installed separately and run as
  its own program.

## Installation

```
uv tool install dsr-version-swapper
```

or, from a checkout, `uv tool install .`.

## Usage

Download the files that differ between versions (once; you will be asked for
your Steam password and Steam Guard code the first time):

```
dsr-version-swapper fetch --user <your steam account name>
```

See the versions you can choose, and which one is installed:

```
dsr-version-swapper list
dsr-version-swapper status
```

Switch the installed game, then launch it through Steam as usual:

```
dsr-version-swapper switch 1.0.1.2
dsr-version-swapper switch 1.0.3.1    # back to the current Steam build
```

Write each version's `DarkSoulsRemastered.exe` out to a folder, for example to
inspect them:

```
dsr-version-swapper export                 # every version
dsr-version-swapper export 1.0.1.2 --to ~/exes
```

The game's folder is found through Steam's library list; pass
`--game-dir <folder>` before the command to point somewhere else.

### What to know before switching

- **Close the game first.** The tool refuses to switch while it is running
  (override with `--ignore-running`).
- **It will not overwrite files it does not recognise.** If the installed files
  match no known version, `switch` stops. Use Steam's *Verify integrity of game
  files* to get back to a known state, or pass `--force`.
- **Steam can undo a switch.** *Verify integrity* and game updates put the
  current build back. That is the same as `switch 1.0.3.1`.
- **Offline use is strongly recommended.** An older or modified install may
  break the game's online terms and could put your account at risk. Older
  builds may also have known multiplayer security problems.
- Each patch before 1.0.3.1 changed game data as well as the executable, so
  switching the data files matters, not just the `.exe`.

## Where things are kept

The local store follows the XDG base directory convention:

```
${XDG_DATA_HOME:-~/.local/share}/dsr-version-swapper/
    blobs/       each downloaded game file, named by the sha256 of its contents
    download/    scratch space used while fetching (removed afterwards)
    binaries/    default destination for `export`
```

Every file is checked against a recorded sha256 before it is stored, and again
after a switch.

## How it works

`src/dsr_version_swapper/data/dsr_versions.json` records, for every version,
its Steam manifest ids and the sha256 of each of the 33 files that differ (or
that the version lacks). `fetch` asks `depotdownloader` for exactly the files
the store is missing (`-filelist`), newest version first since most files are
shared. `switch` compares those 33 paths in your install against each version's
hashes to see what you have, then copies in the target version's files.

## Development

```
uv sync
./checks
```

`./checks` runs black, ruff (import sorting and linting), mypy (strict),
vulture, and pytest, the same way as in the sibling
`steam-utility-launcher` project.
