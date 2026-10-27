import sys

from .application import main as application_main


def main() -> None:
    sys.exit(application_main())


if __name__ == "__main__":
    main()
