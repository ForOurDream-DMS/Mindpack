# Mindpack

**Turn an LLM Wiki / Markdown knowledge base into a portable runtime context pack for LLMs.**

Mindpack is a local-first Python CLI for compiling a structured Markdown knowledge base into a deterministic, portable context bundle. It is designed for teams and builders who want LLM behavior to carry more than a prompt: a persona, rules, a knowledge graph, provenance, evaluation rubrics, and a ready-to-send runtime adapter payload.

## Why use Mindpack?

Plain prompts are easy to copy, but they are shallow and brittle. RAG systems can retrieve lots of text, but the retrieved context is often unstructured and hard to audit. Fine-tuning can be powerful, but it is difficult to update quickly and does not naturally preserve source provenance.

Mindpack sits in the middle:

- **Portable context**: ship a folder or zip that contains the operating persona, rules, graph, provenance, evals, and runtime sample.
- **Structured source of truth**: author knowledge as a Markdown wiki with frontmatter and `[[wikilinks]]`.
- **Deterministic runtime payloads**: generate repeatable adapter context for the next LLM call.
- **Auditable provenance**: keep relative source paths and SHA-256 hashes for compiled pages.
- **Easy updates**: edit Markdown, compile again, validate, and send the new pack.

## Features

- Initialize an example LLM Wiki with `init-wiki`.
- Compile Markdown wiki pages into a Mindpack directory.
- Validate required pack files, JSON/JSONL structure, rules, provenance, and graph edges.
- Build runtime adapter context with persona, selected rules, relevant graph nodes, graph paths, citations, and the user question fenced as untrusted input.
- Local-first workflow; no hosted service required.
- Standard-library-only package code.
- Exclude `raw/` source notes from compiled Mindpacks.
- Preserve provenance with relative source labels and SHA-256 hashes.
- Validate wikilink graph edges so compiled packs do not contain broken internal links.

## Quickstart

From the repository root:

```bash
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
python3 -m mindpack_kit compile examples/founder-idea-wiki --out dist/founder-idea-evaluator --pack-id mindpack.founder-idea-evaluator --title "Founder Idea Evaluator"
python3 -m mindpack_kit validate dist/founder-idea-evaluator
python3 -m mindpack_kit run dist/founder-idea-evaluator --question "Should this idea continue after strict commerce validation?" --out dist/founder-idea-evaluator/samples/runtime_context.md
```

The quickstart uses a generic public profile:

- Profile: `founder-idea-evaluator`
- Pack ID: `mindpack.founder-idea-evaluator`
- Title: `Founder Idea Evaluator`

## Using Mindpack with an AI agent

Most Mindpack users will probably work through an AI coding agent. The repo includes AI-friendly instructions so an agent can clone, test, compile, validate, and generate runtime context in one pass.

- Read [`AGENTS.md`](AGENTS.md) if you are an AI agent working inside this repo.
- Use [`docs/AI_QUICKSTART.md`](docs/AI_QUICKSTART.md) for a copy-paste prompt you can give to Codex, Claude Code, Cursor, OpenCode, or another coding agent.

One-shot agent prompt:

```text
Clone https://github.com/ForOurDream-DMS/Mindpack, run the tests, generate the bundled Founder Idea Evaluator wiki, compile it into a Mindpack, validate it, and create runtime context for this question: "Should this idea continue after strict commerce validation?" Report the generated files and validation result. Do not publish generated dist output unless I explicitly ask.
```

## Source wiki layout

An LLM Wiki is just a Markdown folder. Pages may include simple YAML-like frontmatter and `[[wikilinks]]`:

```text
examples/founder-idea-wiki/
├── SCHEMA.md
├── index.md
├── log.md
├── concepts/
├── evaluations/
├── personas/
├── raw/
└── rules/
```

`raw/` is for source notes and working material. It can remain in the source wiki, but Mindpack excludes it from compiled output.

## Compiled Mindpack output

A compiled pack is a portable directory:

```text
dist/founder-idea-evaluator/
├── mindpack.yaml              # pack metadata
├── graph.jsonl                # nodes and validated wikilink edges
├── rules.json                 # must / avoid / prefer rules
├── persona.yaml               # primary runtime persona
├── provenance.json            # relative source paths and SHA-256 hashes
├── evals.json                 # rubrics and checklists
├── quality_report.json        # compile-time counts and status
├── README.md                  # pack-local usage notes
└── samples/
    └── runtime_context.md     # deterministic adapter payload example
```

Generated `dist/` output is intentionally ignored by git. Rebuild it locally whenever the source wiki changes.

## Example runtime flow

1. Author or update Markdown pages in the wiki.
2. Run `compile` to build the Mindpack.
3. Run `validate` to catch missing files, invalid JSON/JSONL, missing rules, provenance mismatches, or unresolved graph edges.
4. Run `run --question ...` to produce a deterministic runtime context payload.
5. Pass that payload to your LLM adapter as context for the next model call.

The runtime payload is not a final answer. It is the grounded context an LLM can use to answer with the pack's persona, rules, graph references, and citations.

## What Mindpack is / is not

Mindpack is:

- A local compiler from Markdown wiki folders to portable LLM context packs.
- A lightweight structure for persona, rules, graph records, provenance, and evals.
- A deterministic runtime context builder for adapter pipelines.
- A simple format you can inspect, diff, zip, and regenerate.

Mindpack is not:

- A vector database or full RAG platform.
- A fine-tuning system.
- A hosted agent service.
- A prompt marketplace.
- A final-answer generator by itself.

## Development and testing

The package code uses only the Python standard library. The test suite uses `pytest`.

```bash
python3 -m pytest -q
```

Useful manual checks:

```bash
python3 -m mindpack_kit --help
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
python3 -m mindpack_kit compile examples/founder-idea-wiki --out dist/founder-idea-evaluator --pack-id mindpack.founder-idea-evaluator --title "Founder Idea Evaluator"
python3 -m mindpack_kit validate dist/founder-idea-evaluator
```

## License

MIT
