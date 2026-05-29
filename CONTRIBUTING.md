# Contributing to Mindpack

Thanks for helping improve Mindpack. This project is intentionally small, local-first, and privacy-aware. Contributions should keep those properties intact.

## Contribution workflow

1. Fork the repository.
2. Create a focused branch:

   ```bash
   git checkout -b docs/improve-example
   ```

3. Make a small, reviewable change.
4. Run the local checks from the repository root:

   ```bash
   python3 -m pytest -q
   python3 -m mindpack_kit --help
   ```

5. Open a pull request and fill out the PR template.

## Good first contributions

Good first issues usually fit one of these shapes:

- Improve documentation or examples.
- Add public-safe sample Mindpack content.
- Clarify command output or error messages.
- Add tests for an existing CLI behavior.
- Improve validation messages without changing the public format.

Please keep the scope narrow. A small PR that is easy to review is much better than a broad rewrite.

## Privacy and safety rules

Mindpack can turn conversations and knowledge bases into runtime context packs, so privacy is part of the core design.

Do not commit:

- Real personal conversations, chat exports, or private notes.
- Raw source logs under `raw/conversations/`.
- Generated review queues such as `review/pending.jsonl`, `review/accepted.jsonl`, or `review/rejected.jsonl`.
- API keys, tokens, credentials, private URLs, or local absolute paths.
- Customer data, company-confidential data, paid-course/book dumps, or private community content without rights.

Use synthetic examples. If a sample looks like it might identify a real person, company, customer, or private workspace, rewrite it before opening a PR.

## Design principles

- **Local-first**: no hosted service or external network dependency is required for the core workflow.
- **Standard-library package code**: keep runtime package code dependency-free unless there is a strong reason to add one.
- **Deterministic output**: generated Mindpacks should be reproducible and diff-friendly.
- **Explicit review**: raw conversations may produce candidates, but only approved records should become compiled ontology.
- **Portable format**: output should remain inspectable as Markdown, JSON, JSONL, and YAML-like text.
- **Public-safe defaults**: generated `dist/`, raw conversations, and review queues should remain untracked unless a maintainer explicitly decides otherwise.

## Development setup

No install is required when running from the repository root:

```bash
python3 -m pytest -q
python3 -m mindpack_kit --help
```

Optional editable install:

```bash
python3 -m pip install -e .
mindpack-kit --help
```

## Manual smoke tests

### Markdown wiki flow

```bash
python3 -m mindpack_kit init-wiki --out examples/founder-idea-wiki --profile founder-idea-evaluator
python3 -m mindpack_kit compile examples/founder-idea-wiki --out dist/founder-idea-evaluator --pack-id mindpack.founder-idea-evaluator --title "Founder Idea Evaluator"
python3 -m mindpack_kit validate dist/founder-idea-evaluator
python3 -m mindpack_kit run dist/founder-idea-evaluator --question "Should this idea continue after strict commerce validation?" --out dist/founder-idea-evaluator/samples/runtime_context.md
```

### Conversation-to-ontology flow

Use synthetic text only:

```bash
mkdir -p /tmp/mindpack-demo
printf '%s\n' \
  'Concept: Review Queue - Candidate records wait for explicit approval.' \
  'Must: Approved ontology must exclude raw conversation transcripts.' \
  'Prefer: Keep the canonical ontology file-first and git-friendly.' \
  > /tmp/mindpack-demo/conversation.md
python3 -m mindpack_kit init-ontology --out /tmp/mindpack-demo/ontology --pack-id mindpack.demo --title "Demo Ontology"
python3 -m mindpack_kit ingest-conversation /tmp/mindpack-demo/conversation.md --ontology /tmp/mindpack-demo/ontology --source-id demo-chat
```

Inspect `/tmp/mindpack-demo/ontology/review/pending.jsonl`, approve only the candidate IDs you want to publish, then compile and validate the pack.

## Pull request checklist

Before opening a PR, confirm:

- [ ] The change is focused and easy to review.
- [ ] Tests pass with `python3 -m pytest -q`.
- [ ] Examples are synthetic and public-safe.
- [ ] No raw conversations, pending review queues, secrets, or local absolute paths are committed.
- [ ] Documentation is updated if behavior changed.
- [ ] Generated `dist/` output is not committed unless a maintainer explicitly requested it.

## Reporting security or privacy issues

If you find a way for private source material, raw conversations, local paths, or secret-like values to leak into compiled public output, please report it as a security/privacy issue instead of posting real private data in a public issue.
