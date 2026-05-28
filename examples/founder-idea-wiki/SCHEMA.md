---
title: LLM Wiki Schema
kind: schema
tags: [schema, mindpack]
---

# LLM Wiki Schema

This source wiki is a small, file-first knowledge graph for an LLM runtime adapter.

## Required conventions

- Every page may start with YAML-like frontmatter bounded by `---`.
- Use `title`, `kind`, `tags`, and optional rule-specific fields such as `rule_type` and `priority`.
- Use `[[wikilinks]]` to declare graph edges between ideas, rules, personas, and evaluations.
- Keep `raw/` for source notes that should not be compiled into the portable Mindpack.

## Kinds

- `persona`: the operating stance and voice of the evaluator.
- `concept`: reusable decision concepts.
- `rule`: must/avoid/prefer decision constraints.
- `evaluation`: repeatable rubric or checklist.
