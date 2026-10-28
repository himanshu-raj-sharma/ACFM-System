"""Command-line entry point for ACFM-Net."""

from __future__ import annotations

import argparse

from . import __version__


def main() -> int:
    """Run the package command-line interface."""
    parser = argparse.ArgumentParser(
        description="ACFM-Net project foundation.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("version",),
        help="Command to run.",
    )
    parser.parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
