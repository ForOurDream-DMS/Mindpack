# AI Quickstart: Install and Use Mindpack in One Pass

This page is for people who use AI coding agents such as Codex, Claude Code, Cursor, OpenCode, or similar tools.

Mindpack works well with AI agents because the project is intentionally file-first, local-first, and deterministic. An agent can clone the repo, run the tests, create a source wiki, compile it, validate it, and generate runtime context for an LLM call without needing a hosted service.

## Give this prompt to your AI agent

Copy this into your AI coding agent:

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
