# Mindpack Conversation JSONL

Mindpack uses a small common JSONL format between source-specific chat exports and the ontology workflow.

```jsonl
{"record_type":"conversation_turn","source":"codex","source_id":"demo-chat","conversation_id":"demo-chat","turn":1,"role":"user","text":"Concept: Review Queue - Candidate records wait for approval.","sha256":"..."}
```

Required fields:

- `record_type`: `conversation_turn`
- `source`: `generic`, `codex`, `claude-code`, or another adapter label
- `source_id`: safe local source identifier
- `conversation_id`: stable conversation identifier
- `turn`: 1-based turn number
- `role`: `user`, `assistant`, `system`, `developer`, or `unknown`
- `text`: message text
- `sha256`: SHA-256 of `text`

Optional fields:

- `title`: human-readable title
- `url`: source URL, only if you intentionally include it

## Normalize a local export

```bash
python3 -m mindpack_kit import-chat ./agent-export.jsonl \
  --source auto \
  --out /tmp/mindpack-demo/conversation.jsonl \
  --source-id demo-agent-chat
```

`--source auto` detects bundled Codex/Claude Code fixture markers when present and otherwise falls back to generic parsing. For real exports, force `--source codex`, `--source claude-code`, or `--source generic` if you know the file shape.

Supported MVP inputs:

- Markdown/text with `User:`, `Assistant:`, `System:`, or `Developer:` prefixes.
- Generic JSON/JSONL records with `role` plus `text`, `content`, or `message`.
- Codex-like JSONL message events with text/input_text/output_text blocks.
- Claude Code-like JSONL message records with text blocks.

Provider metadata, tool calls, tool results, commands, cwd/workspace paths, and environment-like fields are not copied into the normalized Conversation JSONL.

## Convert to ontology

Conversation JSONL is still raw source material. Mindpack extracts only lines with explicit ontology tags:

- `Concept:`
- `Rule:`
- `Must:`
- `Avoid:`
- `Prefer:`
- `Preference:`
- `Claim:`
- `Case:`

```bash
python3 -m mindpack_kit init-ontology \
  --out /tmp/mindpack-demo/ontology \
  --pack-id mindpack.demo \
  --title "Demo Ontology"

python3 -m mindpack_kit ingest-conversation \
  /tmp/mindpack-demo/conversation.jsonl \
  --ontology /tmp/mindpack-demo/ontology \
  --source-id demo-agent-chat
```

Review pending candidates before approval:

```bash
python3 - <<'PY'
import json
from pathlib import Path
pending = Path('/tmp/mindpack-demo/ontology/review/pending.jsonl')
for line in pending.read_text(encoding='utf-8').splitlines():
    if line.strip():
        item = json.loads(line)
        print(item['id'], item.get('kind'), item.get('rule_type', ''), item.get('label'))
PY
```

Approve explicit candidate IDs:

```bash
python3 -m mindpack_kit approve-candidates \
  /tmp/mindpack-demo/ontology \
  --candidate-id cand_REPLACE_ME
```

Then compile, validate, and write runtime context:

```bash
python3 -m mindpack_kit compile-ontology \
  /tmp/mindpack-demo/ontology \
  --out /tmp/mindpack-demo/pack \
  --pack-id mindpack.demo \
  --title "Demo Ontology"

python3 -m mindpack_kit validate /tmp/mindpack-demo/pack

python3 -m mindpack_kit run \
  /tmp/mindpack-demo/pack \
  --question "What should the next model remember?" \
  --out /tmp/mindpack-demo/pack/samples/runtime_context.md
```

Apply `/tmp/mindpack-demo/pack/samples/runtime_context.md` to your own model as the system/developer/context message before the next user question:

```python
from pathlib import Path
runtime_context = Path('/tmp/mindpack-demo/pack/samples/runtime_context.md').read_text(encoding='utf-8')
messages = [
    {'role': 'system', 'content': runtime_context},
    {'role': 'user', 'content': 'Use this Mindpack context. What should I do next?'},
]
```

For a synthetic or already-reviewed export, `ontology-workflow --approve-all-tagged` can run import, current-import approval, compile, validate, and runtime context in one command:

```bash
python3 -m mindpack_kit ontology-workflow ./agent-export.jsonl \
  --source auto \
  --work-dir /tmp/mindpack-demo \
  --pack-id mindpack.demo \
  --title "Demo Ontology" \
  --question "What should the next model remember?" \
  --approve-all-tagged
```

`approve-candidates --all` approves every pending candidate in a workspace. `ontology-workflow --approve-all-tagged` approves only candidates created by the current import. Both are for synthetic or already-reviewed data only; do not use them blindly on private exports.

## Privacy rules

- Raw exports are private working material.
- Do not commit raw exports, `raw/conversations/`, or review queues.
- Do not ask a cloud coding agent to read raw exports unless you accept sharing that content with the provider.
- Compiled Mindpacks should contain only approved ontology entries, not untagged transcript text.
- Prefer hash-based source IDs when filenames contain customer names, project names, or other sensitive labels.
