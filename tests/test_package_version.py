from dsr_version_swapper import __version__


def test_version_defined() -> None:
    assert bool(__version__)
