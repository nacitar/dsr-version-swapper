import re

from dsr_version_swapper.versions import EXE_FILE, load_version_data


def test_real_data_is_consistent() -> None:
    data = load_version_data()
    assert data.names == [
        "1.0.1.0",
        "1.0.1.1",
        "1.0.1.2",
        "1.0.3.0",
        "1.0.3.1",
    ]
    assert data.newest.name == "1.0.3.1"
    assert EXE_FILE in data.paths
    for version in data.versions:
        assert version.content_manifest.isdigit()
        assert version.exe_manifest.isdigit()
        digests = data.files[version.name]
        assert set(digests) == set(data.paths)
        assert digests[EXE_FILE] is not None
        for digest in digests.values():
            assert digest is None or re.fullmatch(r"[0-9a-f]{64}", digest)


def test_every_old_version_differs_from_the_newest() -> None:
    data = load_version_data()
    newest = data.files[data.newest.name]
    for version in data.versions[:-1]:
        assert data.files[version.name] != newest
