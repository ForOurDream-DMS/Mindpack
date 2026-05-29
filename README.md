# Mindpack

**Turn conversations and Markdown knowledge bases into portable runtime context packs for LLMs.**

Mindpack is a local-first Python CLI for compiling reviewed knowledge into deterministic, portable context bundles. It can compile a structured Markdown wiki, or it can accumulate explicit ontology candidates from LLM conversation logs and promote only reviewed records into an AI-ready ontology pack. It is designed for teams and builders who want LLM behavior to carry more than a prompt: a persona, rules, an ontology/knowledge graph, provenance, evaluation rubrics, and a ready-to-send runtime adapter payload.

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
- Initialize a local ontology workspace with `init-ontology`.
- Ingest LLM conversation logs as raw sources and extract explicit ontology candidates with `ingest-conversation`.
- Promote only reviewed candidate IDs into approved ontology with `approve-candidates`.
- Compile approved ontology entries into a Mindpack directory with `compile-ontology`.
- Compile Markdown wiki pages into a Mindpack directory.
- Validate required pack files, JSON/JSONL structure, rules, provenance, and graph edges.
- Build runtime adapter context with persona, selected rules, relevant graph nodes, graph paths, citations, and the user question fenced as untrusted input.
- Local-first workflow; no hosted service required.
- Standard-library-only package code.
- Exclude `raw/` source notes from compiled Mindpacks.
- Preserve provenance with relative source labels and SHA-256 hashes.
- Validate wikilink graph edges so compiled packs do not contain broken internal links.

## Quickstart: conversation logs to an ontology pack

Mindpack can treat LLM conversations as raw source material, extract explicit ontology candidates, and compile only approved records into a portable runtime pack. This keeps raw chat logs out of the compiled pack by default.

From the repository root:

```bash
mkdir -p /tmp/mindpack-demo
printf '%s\n' \
  'Concept: Review Queue - Candidate records wait for explicit approval.' \
  'Must: Approved ontology must exclude raw conversation transcripts.' \
  'Prefer: Keep the canonical ontology file-first and git-friendly.' \
  'This ordinary chat line stays raw only and is not a candidate.' \
  > /tmp/mindpack-demo/conversation.md

python3 -m mindpack_kit init-ontology --out /tmp/mindpack-demo/ontology --pack-id mindpack.demo-ontology --title "Demo Ontology"
python3 -m mindpack_kit ingest-conversation /tmp/mindpack-demo/conversation.md --ontology /tmp/mindpack-demo/ontology --source-id demo-chat

# Inspect /tmp/mindpack-demo/ontology/review/pending.jsonl, then approve explicit candidate IDs.
python3 - <<'PY'
import json, subprocess
from pathlib import Path
pending = Path('/tmp/mindpack-demo/ontology/review/pending.jsonl')
ids = [json.loads(line)['id'] for line in pending.read_text().splitlines() if line.strip()][:2]
if not ids:
    raise SystemExit('no pending candidates found')
subprocess.check_call(['python3', '-m', 'mindpack_kit', 'approve-candidates', '/tmp/mindpack-demo/ontology', *sum((['--candidate-id', item] for item in ids), [])])
PY

python3 -m mindpack_kit compile-ontology /tmp/mindpack-demo/ontology --out /tmp/mindpack-demo/pack --pack-id mindpack.demo-ontology --title "Demo Ontology"
python3 -m mindpack_kit validate /tmp/mindpack-demo/pack
python3 -m mindpack_kit run /tmp/mindpack-demo/pack --question "How should approved ontology handle raw conversations?" --out /tmp/mindpack-demo/pack/samples/runtime_context.md
```

The ontology workflow has four explicit stages:

1. **Raw conversation**: a local LLM conversation log is stored under `raw/conversations/`.
2. **Candidates**: only explicit tagged lines such as `Concept:`, `Must:`, `Avoid:`, `Prefer:`, `Preference:`, `Claim:`, and `Case:` become pending records.
3. **Review**: candidate IDs are inspected and approved explicitly; there is no automatic merge into the ontology.
4. **Approved ontology**: only approved records are compiled into `ontology.jsonl`, graph nodes, rules, provenance, and runtime context.

Generated `dist/` output is intentionally ignored by git. Raw conversations and generated review queues are also ignored so private source logs are not committed accidentally.

## Quickstart: Markdown wiki to Mindpack

From the repository root:

```bash
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
python3 -m mindpack_kit compile examples/founder-idea-wiki --out dist/founder-idea-evaluator --pack-id mindpack.founder-idea-evaluator --title "Founder Idea Evaluator"
python3 -m mindpack_kit validate dist/founder-idea-evaluator
python3 -m mindpack_kit run dist/founder-idea-evaluator --question "Should this idea continue after strict commerce validation?" --out dist/founder-idea-evaluator/samples/runtime_context.md
```

The wiki quickstart uses a generic public profile:

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
├── ontology.jsonl             # approved ontology entries, if any
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
- A local conversation-to-ontology workflow where raw logs produce pending candidates and explicit approval produces runtime context.
- A lightweight structure for persona, rules, graph records, ontology records, provenance, and evals.
- A deterministic runtime context builder for adapter pipelines.
- A simple format you can inspect, diff, zip, and regenerate.

Mindpack is not:

- A vector database or full RAG platform.
- A fine-tuning system.
- A hosted agent service.
- A prompt marketplace.
- A final-answer generator by itself.

## Contributing

Contributions are welcome through fork + pull request. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), and use the issue templates for bugs, feature requests, or documentation/example improvements.

Mindpack is privacy-sensitive by design. Please use synthetic examples only, and do not commit real conversations, raw source logs, generated review queues, credentials, private paths, or customer data.

Useful community entry points:

- [`good first issue`](https://github.com/ForOurDream-DMS/Mindpack/labels/good%20first%20issue) — small starter tasks.
- [`help wanted`](https://github.com/ForOurDream-DMS/Mindpack/labels/help%20wanted) — areas where outside contribution is especially useful.
- [`SECURITY.md`](SECURITY.md) — how to report privacy or security-sensitive issues.

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
