# Web Chat Capture

Mindpack does not depend on scraping a provider account. The safest MVP is a local export file: copy selected chat text, use an official provider export, or use the simple bookmarklet source in `tools/mindpack-capture-bookmarklet.js`.

## Bookmarklet behavior

The bookmarklet is intentionally limited:

- no network requests
- no API keys
- no login bypass
- no hidden bulk export
- no automatic upload
- selected text first; visible page text only if nothing is selected

It may miss collapsed, unloaded, virtualized, image-only, attachment, or tool-output content. It may also include UI chrome. Review the downloaded file before ingestion.

## Install

1. Show your browser bookmarks bar.
2. Create a new bookmark.
3. Name it `Mindpack export visible chat`.
4. Generate the bookmarklet URL from the repo root:

   ```bash
   python3 - <<'PY'
   from pathlib import Path
   import re
   src = Path('tools/mindpack-capture-bookmarklet.js').read_text(encoding='utf-8')
   src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
   src = re.sub(r'\s+', ' ', src).strip()
   print('javascript:' + src)
   PY
   ```

5. Paste the printed `javascript:` URL into the bookmark URL field.
6. Open a conversation page.
7. Select only the messages you want, then click the bookmarklet.
8. Save the downloaded Markdown under a private folder such as `/tmp/mindpack-export/` or a gitignored `private-exports/` folder.

## Prepare the export

For better ontology extraction, add a tagged summary to the end of the chat before exporting, or edit the exported Markdown locally:

```text
Concept: Review Queue - Candidate records wait for explicit approval.
Must: Raw transcripts stay local and are not compiled directly.
Prefer: Keep approved ontology records short and reviewable.
```

Mindpack extracts only tagged lines. Untagged chat remains raw source material.

## Run locally

Safe review-first flow:

```bash
python3 -m mindpack_kit ontology-workflow /tmp/mindpack-export/chat.md \
  --source generic \
  --work-dir /tmp/mindpack-export/work \
  --pack-id mindpack.local-memory \
  --title "Local Memory" \
  --question "What should the assistant remember?"
```

The command above stops before compile. Review pending candidates:

```bash
python3 - <<'PY'
import json
from pathlib import Path
pending = Path('/tmp/mindpack-export/work/ontology/review/pending.jsonl')
for line in pending.read_text(encoding='utf-8').splitlines():
    if line.strip():
        item = json.loads(line)
        print(item['id'], item.get('kind'), item.get('rule_type', ''), item.get('label'))
PY
```

Approve selected IDs, compile, validate, and write model-ready runtime context:

```bash
python3 -m mindpack_kit approve-candidates /tmp/mindpack-export/work/ontology \
  --candidate-id cand_REPLACE_ME

python3 -m mindpack_kit compile-ontology /tmp/mindpack-export/work/ontology \
  --out /tmp/mindpack-export/work/pack \
  --pack-id mindpack.local-memory \
  --title "Local Memory"

python3 -m mindpack_kit validate /tmp/mindpack-export/work/pack
python3 -m mindpack_kit run /tmp/mindpack-export/work/pack \
  --question "What should the assistant remember?" \
  --out /tmp/mindpack-export/work/pack/samples/runtime_context.md
```

Apply `samples/runtime_context.md` as the system/developer/context message for your next model call. If the export is synthetic or already reviewed, you can run the one-command path by adding `--approve-all-tagged` to `ontology-workflow`.
