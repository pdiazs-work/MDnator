#!/usr/bin/env python3
"""MDnator CLI — convert documents to Markdown from the terminal.

Usage:
    python cli.py input.pdf
    python cli.py input.docx -o output.md
    python cli.py *.txt -o combined.md
"""

import argparse
import sys
from pathlib import Path

from src.core.converter import DocumentConverter
from src.core.validators import validate_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdnator",
        description="Convert documents to Markdown.",
    )
    parser.add_argument("inputs", nargs="+", metavar="FILE", help="Input file(s)")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write output to FILE instead of stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    converter = DocumentConverter()
    results = []
    errors = []

    for path in args.inputs:
        ok, msg = validate_file(path)
        if not ok:
            print(f"[skip] {path}: {msg}", file=sys.stderr)
            errors.append(path)
            continue
        try:
            md = converter.convert(path)
            header = f"## {Path(path).name}\n\n" if len(args.inputs) > 1 else ""
            results.append(f"{header}{md}")
        except RuntimeError as exc:
            print(f"[error] {path}: {exc}", file=sys.stderr)
            errors.append(path)

    if not results:
        print("No files converted.", file=sys.stderr)
        return 1

    output = "\n\n---\n\n".join(results)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Saved to {args.output}")
    else:
        print(output)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
