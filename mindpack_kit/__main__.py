"""Command line interface for Mindpack."""

from __future__ import annotations

import argparse
import sys

from .compiler import compile_mindpack, validate_pack, write_runtime_context
from .domains import discover_domains
from .importers import CHAT_SOURCE_CHOICES, import_chat_export, run_ontology_workflow
from .ontology import approve_candidates, compile_ontology_pack, ingest_conversation, init_ontology_workspace
from .wiki import init_wiki


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m mindpack_kit", description="Compile LLM Wiki folders into portable Mindpacks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-wiki", help="Create a source LLM Wiki folder from a profile template.")
    init_parser.add_argument("--out", required=True, help="Output wiki directory")
    init_parser.add_argument("--profile", required=True, help="Profile name, e.g. founder-idea-evaluator")

    init_ontology_parser = subparsers.add_parser("init-ontology", help="Create a local ontology workspace.")
    init_ontology_parser.add_argument("--out", required=True, help="Output ontology workspace directory")
    init_ontology_parser.add_argument("--pack-id", required=True, help="Stable Mindpack ID for this ontology")
    init_ontology_parser.add_argument("--title", required=True, help="Human-readable ontology title")

    ingest_parser = subparsers.add_parser("ingest-conversation", help="Store a conversation as raw source and extract explicit ontology candidates.")
    ingest_parser.add_argument("source_file", help="Conversation text, markdown, or JSONL file")
    ingest_parser.add_argument("--ontology", required=True, help="Ontology workspace directory")
    ingest_parser.add_argument("--source-id", help="Stable source identifier used for raw/conversations/<source-id>.jsonl")

    import_parser = subparsers.add_parser("import-chat", help="Normalize a local AI-agent chat export into Mindpack Conversation JSONL.")
    import_parser.add_argument("source_file", help="Local chat export file (.md, .txt, .json, or .jsonl)")
    import_parser.add_argument("--source", choices=CHAT_SOURCE_CHOICES, default="auto", help="Chat export source format")
    import_parser.add_argument("--out", help="Output Conversation JSONL path")
    import_parser.add_argument("--ontology", help="Optional ontology workspace to ingest into after normalization")
    import_parser.add_argument("--source-id", help="Stable source identifier used for raw/conversations/<source-id>.jsonl")
    import_parser.add_argument("--conversation-id", help="Stable conversation identifier to write into normalized JSONL")
    import_parser.add_argument("--title", help="Optional human-readable conversation title")
    import_parser.add_argument("--url", help="Optional source URL to include in normalized JSONL")

    approve_parser = subparsers.add_parser("approve-candidates", help="Promote explicit pending candidate IDs into approved ontology.")
    approve_parser.add_argument("ontology_dir", help="Ontology workspace directory")
    approve_parser.add_argument("--candidate-id", action="append", default=[], help="Candidate ID to approve; repeat for multiple IDs")
    approve_parser.add_argument("--all", action="store_true", help="Approve all pending candidates after review")

    compile_ontology_parser = subparsers.add_parser("compile-ontology", help="Compile approved ontology entries into a Mindpack directory.")
    compile_ontology_parser.add_argument("ontology_dir", help="Ontology workspace directory")
    compile_ontology_parser.add_argument("--out", required=True, help="Output Mindpack directory")
    compile_ontology_parser.add_argument("--pack-id", required=True, help="Stable Mindpack ID")
    compile_ontology_parser.add_argument("--title", required=True, help="Human-readable Mindpack title")

    workflow_parser = subparsers.add_parser("ontology-workflow", help="Import local chat and extract candidates; with --approve-all-tagged, also compile, validate, and write runtime context.")
    workflow_parser.add_argument("source_file", help="Local chat export or conversation file")
    workflow_parser.add_argument("--work-dir", required=True, help="Working directory for ontology workspace and compiled pack")
    workflow_parser.add_argument("--pack-id", required=True, help="Stable Mindpack ID")
    workflow_parser.add_argument("--title", required=True, help="Human-readable Mindpack title")
    workflow_parser.add_argument("--question", required=True, help="Question used to generate runtime context")
    workflow_parser.add_argument("--source", choices=CHAT_SOURCE_CHOICES, default="auto", help="Chat export source format")
    workflow_parser.add_argument("--source-id", help="Stable source identifier used for raw/conversations/<source-id>.jsonl")
    workflow_parser.add_argument("--approve-all-tagged", action="store_true", help="Approve current import's tagged candidates and compile immediately; use only for synthetic or already-reviewed exports")

    discover_domains_parser = subparsers.add_parser("discover-domains", help="Discover multiple Mindpack domains from source files or folders.")
    discover_domains_parser.add_argument("source_paths", nargs="+", help="Source text file or directory; repeat for multiple roots")
    discover_domains_parser.add_argument("--out", required=True, help="Output domain registry directory")

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

        if args.command == "init-ontology":
            written = init_ontology_workspace(args.out, args.pack_id, args.title)
            print(f"Created ontology workspace at {args.out} ({len(written)} files).")
            return 0

        if args.command == "ingest-conversation":
            report = ingest_conversation(args.source_file, args.ontology, args.source_id)
            print(
                f"Stored raw conversation at {report['raw_path']} and extracted "
                f"{report['candidate_count']} candidates into {report['pending_path']}."
            )
            return 0

        if args.command == "import-chat":
            report = import_chat_export(
                args.source_file,
                args.out,
                ontology_dir=args.ontology,
                source=args.source,
                source_id=args.source_id,
                conversation_id=args.conversation_id,
                title=args.title,
                url=args.url,
            )
            if args.ontology:
                print(
                    f"Exported {report['turn_count']} turns to {report['out_path']} "
                    f"as source_id {report['source_id']}; ingested into {args.ontology} "
                    f"and extracted {report['candidate_count']} candidates into {report['pending_path']}."
                )
            else:
                print(f"Exported {report['turn_count']} turns to {report['out_path']} as source_id {report['source_id']}.")
            return 0

        if args.command == "approve-candidates":
            report = approve_candidates(args.ontology_dir, args.candidate_id, args.all)
            print(f"Approved {report['approved_count']} candidates into {report['approved_path']}.")
            return 0

        if args.command == "compile-ontology":
            report = compile_ontology_pack(args.ontology_dir, args.out, args.pack_id, args.title)
            print(
                "Compiled ontology Mindpack at "
                f"{args.out} ({report['ontology_entry_count']} approved entries, "
                f"{report['graph_node_count']} graph nodes)."
            )
            return 0

        if args.command == "ontology-workflow":
            report = run_ontology_workflow(
                args.source_file,
                args.work_dir,
                pack_id=args.pack_id,
                title=args.title,
                question=args.question,
                source=args.source,
                source_id=args.source_id,
                approve_all_tagged=args.approve_all_tagged,
            )
            if report["status"] == "pending_review":
                print(
                    f"Imported {report['turn_count']} turns and extracted {report['candidate_count']} candidates. "
                    f"Review pending candidates at {report['ontology_dir']}/review/pending.jsonl, then run approve-candidates and compile-ontology."
                )
            else:
                print(
                    f"Compiled ontology Mindpack at {report['pack_dir']} "
                    f"({report['ontology_entry_count']} approved entries, {report['graph_node_count']} graph nodes)."
                )
                print(f"VALID: {report['pack_dir']}")
                print(f"Wrote runtime context to {report['runtime_context_path']}")
            return 0

        if args.command == "discover-domains":
            report = discover_domains(args.source_paths, args.out)
            print(
                "Discovered "
                f"{report['domain_count']} domains from {report['source_count']} sources "
                f"with {report['pending_domain_candidate_count']} pending domain candidates "
                f"into {args.out}."
            )
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
