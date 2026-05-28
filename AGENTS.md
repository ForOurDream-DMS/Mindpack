# AGENTS.md — AI Agent Quickstart for Mindpack

This repository is designed to be used by AI coding agents as well as humans. If you are an AI agent, follow this file first.

## What this repo does

Mindpack compiles an LLM Wiki / Markdown knowledge base into a portable runtime context pack for LLMs.

A compiled Mindpack includes:

- `mindpack.yaml` — pack metadata
- `graph.jsonl` — nodes and validated wikilink edges
- `rules.json` — `must`, `avoid`, and `prefer` rules
- `persona.yaml` — primary runtime persona
- `provenance.json` — relative source paths and SHA-256 hashes
- `evals.json` — evaluation rubrics/checklists
- `samples/runtime_context.md` — context payload to send to an LLM

## One-pass setup and smoke test

Run from the repository root:

```bash
python3 -m pytest -q
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
python3 -m mindpack_kit compile examples/founder-idea-wiki --out dist/founder-idea-evaluator --pack-id mindpack.founder-idea-evaluator --title "Founder Idea Evaluator"
python3 -m mindpack_kit validate dist/founder-idea-evaluator
python3 -m mindpack_kit run dist/founder-idea-evaluator --question "Should this idea continue after strict commerce validation?" --out dist/founder-idea-evaluator/samples/runtime_context.md
```

Expected result:

- tests pass
- `dist/founder-idea-evaluator/` is created
- validation prints `VALID`
- `dist/founder-idea-evaluator/samples/runtime_context.md` exists

## Optional editable install

No install is required when running from the repository root. If the user asks for a local command, install editable mode:

```bash
python3 -m pip install -e .
mindpack-kit --help
```

## Common tasks

### Create a new wiki from the bundled example profile

```bash
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
```

### Compile a wiki into a Mindpack

```bash
python3 -m mindpack_kit compile <wiki_dir> --out <pack_dir> --pack-id <stable.pack.id> --title "Human Readable Title"
```

### Validate a compiled pack

```bash
python3 -m mindpack_kit validate <pack_dir>
```

### Generate runtime context for an LLM call

```bash
python3 -m mindpack_kit run <pack_dir> --question "Your user question" --out <pack_dir>/samples/runtime_context.md
```

Send the generated runtime context to the next LLM call as grounding context. It is not the final answer by itself.

## Rules for AI agents modifying this repo

- Keep package code standard-library-only unless the user explicitly requests dependencies.
- Do not commit generated `dist/` output unless the user explicitly asks for a packaged artifact.
- Keep example content generic and public-safe.
- Do not add secrets, tokens, private paths, or personal data.
- Run `python3 -m pytest -q` before committing code changes.
- For docs-only changes, still run the test suite unless the user explicitly asks to skip it.
