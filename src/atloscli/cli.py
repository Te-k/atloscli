"""Command line entry point for atloscli."""

import argparse
import json
import sys
from pathlib import Path

import requests

from atloscli import __version__
from atloscli.atlos import DEFAULT_BASE_URL, Atlos, AtlosError

CONFIG_PATH = Path.home() / ".config" / "atlos"


def read_api_key(path: Path = CONFIG_PATH) -> str:
    """Return the Atlos API key stored in ``path``."""
    try:
        key = path.read_text().strip()
    except OSError as e:
        raise SystemExit(f"Error: cannot read Atlos API key from {path}: {e}") from e
    if not key:
        raise SystemExit(f"Error: {path} is empty, it should contain an API key")
    return key


def cmd_incidents(atlos: Atlos, args: argparse.Namespace) -> None:
    for incident in atlos.get_incidents():
        if args.json:
            print(json.dumps(incident))
            continue
        slug = incident.get("slug", "")
        status = incident.get("attr_status") or incident.get("status") or ""
        description = (
            incident.get("attr_description") or incident.get("description") or ""
        )
        print(f"{slug}\t{status}\t{description}")


def cmd_incident(atlos: Atlos, args: argparse.Namespace) -> int:
    incident = atlos.get_incident(args.slug)
    if incident is None:
        print(f"Error: incident {args.slug} not found", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(incident, indent=2))
        return 0
    width = max((len(key) for key in incident), default=0)
    for key, value in incident.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        print(f"{key:<{width}}  {'' if value is None else value}")
    return 0


def cmd_materials(atlos: Atlos, args: argparse.Namespace) -> None:
    for material in atlos.get_source_materials():
        if args.json:
            print(json.dumps(material))
            continue
        material_id = material.get("id", "")
        url = material.get("source_url") or material.get("url") or ""
        title = material.get("title") or ""
        print(f"{material_id}\t{url}\t{title}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atloscli", description="Command line tool for Atlos"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help="Base URL of the Atlos instance (default: %(default)s)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    incidents = subparsers.add_parser(
        "incidents", help="List all incidents of the project"
    )
    incidents.add_argument(
        "--json", action="store_true", help="Print each incident as a JSON line"
    )
    incidents.set_defaults(func=cmd_incidents)

    incident = subparsers.add_parser("incident", help="Show a single incident")
    incident.add_argument("slug", help="Incident ID, e.g. 7X7YFH or CIV-7X7YFH")
    incident.add_argument("--json", action="store_true", help="Print as JSON")
    incident.set_defaults(func=cmd_incident)

    materials = subparsers.add_parser(
        "materials", help="List all source material of the project"
    )
    materials.add_argument(
        "--json", action="store_true", help="Print each source material as a JSON line"
    )
    materials.set_defaults(func=cmd_materials)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    atlos = Atlos(read_api_key(), base_url=args.url)
    try:
        return args.func(atlos, args) or 0
    except (AtlosError, requests.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
