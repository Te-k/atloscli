"""Command line entry point for atloscli."""

import argparse

import requests

from atloscli import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atloscli", description="Command line tool for Atlos"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--url",
        default="https://platform.atlos.org",
        help="Base URL of the Atlos instance",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        response = requests.get(args.url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: {e}")
        return 1
    print(f"{args.url}: HTTP {response.status_code}")
    return 0
