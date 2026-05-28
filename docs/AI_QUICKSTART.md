# AI Quickstart: Install and Use Mindpack in One Pass

This page is for people who use AI coding agents such as Codex, Claude Code, Cursor, OpenCode, or similar tools.

Mindpack works well with AI agents because the project is intentionally file-first, local-first, and deterministic. An agent can clone the repo, run the tests, create a source wiki, compile it, validate it, and generate runtime context for an LLM call without needing a hosted service.

## Give this prompt to your AI agent

Copy this into your AI coding agent for the Markdown wiki workflow:

```text
Clone and use Mindpack.

Goal:
- Install/run the local Mindpack CLI.
- Generate the bundled Founder Idea Evaluator example.
- Compile it into a Mindpack.
- Validate the pack.
- Generate runtime context for an LLM question.
- Report the generated files and validation result.

Commands:

git clone https://github.com/ForOurDream-DMS/Mindpack.git
cd Mindpack
python3 -m pytest -q
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
python3 -m mindpack_kit compile examples/founder-idea-wiki --out dist/founder-idea-evaluator --pack-id mindpack.founder-idea-evaluator --title "Founder Idea Evaluator"
python3 -m mindpack_kit validate dist/founder-idea-evaluator
python3 -m mindpack_kit run dist/founder-idea-evaluator --question "Should this idea continue after strict commerce validation?" --out dist/founder-idea-evaluator/samples/runtime_context.md

Expected:
- Tests pass.
- Validation prints VALID.
- Runtime context is written to dist/founder-idea-evaluator/samples/runtime_context.md.

Do not publish generated dist output unless I explicitly ask.
```

## Conversation-to-ontology agent prompt

Use this prompt when you want an agent to test the open-source ontology workflow without committing private conversations:

```text
Clone and use Mindpack's ontology workflow.

Goal:
- Run the local Mindpack CLI.
- Create a synthetic conversation file with explicit ontology tags.
- Initialize an ontology workspace.
- Ingest the conversation as raw source and extract pending candidates.
- Inspect pending candidates and approve only explicit candidate IDs.
- Compile the approved ontology into a Mindpack.
- Validate the pack.
- Generate runtime context for an LLM question.
- Report the generated files and validation result.

Commands:

git clone https://github.com/ForOurDream-DMS/Mindpack.git
cd Mindpack
python3 -m pytest -q
mkdir -p /tmp/mindpack-demo
printf '%s\n' \
  'Concept: Review Queue - Candidate records wait for explicit approval.' \
  'Must: Approved ontology must exclude raw conversation transcripts.' \
  'Prefer: Keep the canonical ontology file-first and git-friendly.' \
  > /tmp/mindpack-demo/conversation.md
python3 -m mindpack_kit init-ontology --out /tmp/mindpack-demo/ontology --pack-id mindpack.demo --title "Demo Ontology"
python3 -m mindpack_kit ingest-conversation /tmp/mindpack-demo/conversation.md --ontology /tmp/mindpack-demo/ontology --source-id demo-chat
python3 - <<'PY'
import json, subprocess
from pathlib import Path
pending = Path('/tmp/mindpack-demo/ontology/review/pending.jsonl')
ids = [json.loads(line)['id'] for line in pending.read_text().splitlines() if line.strip()][:2]
if not ids:
    raise SystemExit('no pending candidates found')
subprocess.check_call(['python3', '-m', 'mindpack_kit', 'approve-candidates', '/tmp/mindpack-demo/ontology', *sum((['--candidate-id', item] for item in ids), [])])
PY
python3 -m mindpack_kit compile-ontology /tmp/mindpack-demo/ontology --out /tmp/mindpack-demo/pack --pack-id mindpack.demo --title "Demo Ontology"
python3 -m mindpack_kit validate /tmp/mindpack-demo/pack
python3 -m mindpack_kit run /tmp/mindpack-demo/pack --question "How should approved ontology handle raw conversations?" --out /tmp/mindpack-demo/pack/samples/runtime_context.md

Expected:
- Tests pass.
- Pending candidates are generated from explicit tagged lines only.
- Validation prints VALID.
- Runtime context includes approved ontology entries and excludes raw untagged chat text.

Do not publish raw conversations, pending review queues, secrets, local absolute paths, or private generated dist output unless I explicitly ask.
```

## Minimal human commands

If you are running it yourself:

```bash
git clone https://github.com/ForOurDream-DMS/Mindpack.git
cd Mindpack
python3 -m pytest -q
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
python3 -m mindpack_kit compile examples/founder-idea-wiki --out dist/founder-idea-evaluator --pack-id mindpack.founder-idea-evaluator --title "Founder Idea Evaluator"
python3 -m mindpack_kit validate dist/founder-idea-evaluator
python3 -m mindpack_kit run dist/founder-idea-evaluator --question "Should this idea continue after strict commerce validation?" --out dist/founder-idea-evaluator/samples/runtime_context.md
```

No API key is required.

## Optional install as a command

From the repo root:

```bash
python3 -m pip install -e .
mindpack-kit --help
```

Then you can run:

```bash
mindpack-kit validate dist/founder-idea-evaluator
```

## How an AI agent should use the output

The generated runtime context is an adapter payload. It should be passed into the next LLM call as grounding context.

Typical flow:

```text
User question
  ↓
mindpack-kit run <pack> --question "..."
  ↓
samples/runtime_context.md
  ↓
LLM receives runtime context + user question
  ↓
LLM answers with the Mindpack persona, rules, graph references, and citations
```

## Why this is useful for AI users

Most AI users do not want to manually re-explain their preferences, rules, domain assumptions, and source material every time.

Mindpack gives an AI agent a repeatable way to load:

- the operating persona
- decision rules
- relevant graph nodes and paths
- source citations
- evaluation rubrics
- provenance

That makes the next LLM call more structured than a plain prompt and easier to update than fine-tuning.
