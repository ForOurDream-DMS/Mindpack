"""Command line interface for Mindpack."""

from __future__ import annotations

import argparse
import sys

from .compiler import compile_mindpack, validate_pack, write_runtime_context
from .wiki import init_wiki


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m mindpack_kit", description="Compile LLM Wiki folders into portable Mindpacks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-wiki", help="Create a source LLM Wiki folder from a profile template.")
    init_parser.add_argument("--out", required=True, help="Output wiki directory")
    init_parser.add_argument("--profile", required=True, help="Profile name, e.g. founder-idea-evaluator")

    compile_parser = subparsers.add_parser("compile", help="Compile a source wiki into a Mindpack directory.")
    compile_parser.add_argument("wiki_dir", help="Source wiki directory")
    compile_parser.add_argument("--out", required=True, help="Output Mindpack directory")
    compile_parser.add_argument("--pack-id", required=True, help="Stable Mindpack ID")
    compile_parser.add_argument("--title", required=True, help="Human-readable Mindpack title")

    validate_parser = subparsers.add_parser("validate", help="Validate a compiled Mindpack directory.")
    validate_parser.add_argument("pack_dir", help="Compiled Mindpack directory")

    run_parser = subparsers.add_parser("run", help="Build deterministic runtime context for a question.")
    run_parser.add_argument("pack_dir", help="Compiled Mindpack directory")
    run_parser.add_argument("--question", required=True, help="Question to ground against the Mindpack")
    run_parser.add_argument("--out", help="Optional output markdown path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init-wiki":
            written = init_wiki(args.out, args.profile)
            print(f"Created wiki at {args.out} ({len(written)} files).")
            return 0

        if args.command == "compile":
            report = compile_mindpack(args.wiki_dir, args.out, args.pack_id, args.title)
            print(
                "Compiled Mindpack at "
                f"{args.out} ({report['compiled_page_count']} pages, "
                f"{report['graph_edge_count']} edges)."
            )
            return 0

        if args.command == "validate":
            valid, messages = validate_pack(args.pack_dir)
            if valid:
                print(f"VALID: {args.pack_dir}")
                return 0
            print(f"INVALID: {args.pack_dir}")
            for message in messages:
                print(f"- {message}")
            return 1

        if args.command == "run":
            context = write_runtime_context(args.pack_dir, args.question, args.out)
            if args.out:
                print(f"Wrote runtime context to {args.out}")
            else:
                print(context)
            return 0

    except Exception as exc:  # pragma: no cover - exercised by CLI failure paths
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
