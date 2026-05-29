# Security Policy

Mindpack is a local-first tool for compiling reviewed knowledge into portable LLM context packs. The most important security class for this project is accidental disclosure of private source material.

## Please report privately

Please use a private security advisory if you find a vulnerability that can expose or publish:

- Raw conversations or private notes.
- Generated review queues such as `review/pending.jsonl`, `review/accepted.jsonl`, or `review/rejected.jsonl`.
- Local absolute paths, usernames, workspace names, private URLs, or secret-like values.
- API keys, tokens, credentials, or environment variable values.
- Customer data, confidential company data, or private community content.

Private advisory link:

https://github.com/ForOurDream-DMS/Mindpack/security/advisories/new

## Public issue safety

For normal bug reports, please use synthetic examples only. Do not paste real private conversations, credentials, customer data, or private paths into public issues.

## Expected design behavior

Mindpack should:

- Ignore generated `dist/` output by default.
- Keep raw conversations and generated review queues out of git by default.
- Compile only explicitly approved ontology records.
- Preserve provenance with public-safe relative source labels.
- Fail closed when public output would contain unsafe source references.
