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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from topo_semantic_adapter.cli_loader import DEFAULT_DELIMITER


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
    parser = argparse.ArgumentParser(
        description="Extract command names from CLI inspection files."
    )
    parser.add_argument(
        "base_path",
        nargs="?",
        default=".",
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
    args = parser.parse_args()

    base = Path(args.base_path)
    if not base.exists():
        print(f"Error: path does not exist: {base}", file=sys.stderr)
        return 1

    result_files = sorted(base.rglob("CommonCollectResult"))
    if not result_files:
        print(f"No CommonCollectResult files found under {base}", file=sys.stderr)
        return 0

    commands: list[str] = []
    file_commands: list[tuple[Path, list[str]]] = []

    for result_file in result_files:
        text = result_file.read_text(encoding="utf-8", errors="ignore")
        cmds = extract_commands(text, args.delimiter)
        file_commands.append((result_file, cmds))
        commands.extend(cmds)

    if args.unique:
        output = sorted(set(commands))
    else:
        output = commands

    for item in output:
        print(item)

    if args.with_file:
        print("\n# Per-file breakdown", file=sys.stderr)
        for result_file, cmds in file_commands:
            print(f"\n# {result_file}", file=sys.stderr)
            for cmd in cmds:
                print(f"  {cmd}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
