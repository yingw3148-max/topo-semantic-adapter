"""Extract command names from CLI inspection files.

Scans a directory tree for ``CommonCollectResult`` files (the production layout
``{site}/inspect/{ip}_{id}/CommonCollectResult``), splits each file by the
Huawei delimiter, and prints the command names.

Usage:
    python examples/extract_commands.py [base_path]

Examples:
    python examples/extract_commands.py tests/fixtures
    python examples/extract_commands.py /data/sites --unique
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT))

from topo_semantic_adapter.cli_loader import DEFAULT_DELIMITER


def _ensure_example_fixtures(default_path: Path) -> None:
    """If the default tests/fixtures directory is empty, regenerate sample files."""
    if not default_path.exists() or not list(default_path.rglob("CommonCollectResult")):
        try:
            from tests.fixtures import write_fixture_site

            write_fixture_site(default_path)
            print(
                f"# Regenerated example fixtures under {default_path}",
                file=sys.stderr,
            )
        except Exception as exc:  # pragma: no cover
            print(
                f"# Could not auto-generate example fixtures: {exc}",
                file=sys.stderr,
            )


def extract_commands(text: str, delimiter: str) -> list[str]:
    """Return command names from a single CommonCollectResult text."""
    commands: list[str] = []
    for part in text.split(delimiter):
        part = part.strip("\r\n")
        if not part.strip():
            continue
        first_line = part.splitlines()[0].strip()
        if first_line:
            commands.append(first_line)
    return commands


def main() -> int:
    default_path = _PROJECT_ROOT / "tests" / "fixtures"

    parser = argparse.ArgumentParser(
        description="Extract command names from CLI inspection files."
    )
    parser.add_argument(
        "base_path",
        nargs="?",
        default=str(default_path),
        help="Root directory to scan for CommonCollectResult files.",
    )
    parser.add_argument(
        "--delimiter",
        default=DEFAULT_DELIMITER,
        help="Delimiter used to separate command blocks.",
    )
    parser.add_argument(
        "--unique",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Deduplicate and sort command names (default: true).",
    )
    parser.add_argument(
        "--with-file",
        action="store_true",
        help="Prefix each command with the source file path.",
    )
    parser.add_argument(
        "--by-site",
        action="store_true",
        help="Group output by site directory (e.g. 湖北大学配置, 南开大学配置).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write output to a file instead of stdout.",
    )
    args = parser.parse_args()

    base = Path(args.base_path)
    if not base.exists():
        print(f"Error: path does not exist: {base}", file=sys.stderr)
        return 1

    if base.resolve() == default_path.resolve():
        _ensure_example_fixtures(default_path)

    def _site_name(result_file: Path) -> str:
        """Guess the site name from the path.

        Walks up from the file towards ``base`` and returns the first directory
        whose name looks like a site folder (ends with '配置'), or the immediate
        child directory of ``base`` as a fallback.
        """
        try:
            rel_parts = result_file.relative_to(base).parts
        except ValueError:
            return base.name
        # Prefer a directory named like 'xx配置'.
        for part in rel_parts[:-1]:
            if part.endswith("配置"):
                return part
        # Otherwise use the top-level subdirectory under base.
        if len(rel_parts) > 1:
            return rel_parts[0]
        return base.name

    result_files = sorted(base.rglob("CommonCollectResult"))
    if not result_files:
        print(f"No CommonCollectResult files found under {base}", file=sys.stderr)
        return 0

    commands: list[str] = []
    file_commands: list[tuple[Path, list[str]]] = []
    site_commands: dict[str, list[str]] = {}

    for result_file in result_files:
        text = result_file.read_text(encoding="utf-8", errors="ignore")
        cmds = extract_commands(text, args.delimiter)
        file_commands.append((result_file, cmds))
        commands.extend(cmds)
        site = _site_name(result_file)
        site_commands.setdefault(site, []).extend(cmds)

    lines: list[str] = []

    if args.by_site:
        for site in sorted(site_commands):
            lines.append(f"# {site}")
            for cmd in sorted(set(site_commands[site])):
                lines.append(f"  {cmd}")
            lines.append("")
    else:
        if args.unique:
            lines = sorted(set(commands))
        else:
            lines = commands

    if args.output:
        out_path = Path(args.output)
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {len(lines)} lines to {out_path}", file=sys.stderr)
    else:
        for line in lines:
            print(line)

    if args.with_file:
        print("\n# Per-file breakdown", file=sys.stderr)
        for result_file, cmds in file_commands:
            print(f"\n# {result_file}", file=sys.stderr)
            for cmd in cmds:
                print(f"  {cmd}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
