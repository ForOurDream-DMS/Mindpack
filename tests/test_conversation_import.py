import json
from pathlib import Path

from test_mindpack_kit import assert_public_text_is_sanitized, read_jsonl, run_cli


TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}


def write_jsonl(path: Path, records):
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def assert_pack_text_excludes(pack_dir: Path, forbidden: str):
    for path in pack_dir.rglob("*"):
        if path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name in {"README", "LICENSE"}):
            assert forbidden not in path.read_text(encoding="utf-8", errors="ignore"), path.relative_to(pack_dir).as_posix()


def test_import_chat_normalizes_generic_json_messages_and_ingests(tmp_path):
    source_path = tmp_path / "agent-export.json"
    out_path = tmp_path / "conversation.jsonl"
    ontology_dir = tmp_path / "ontology"
    source_path.write_text(
        json.dumps(
            {
                "title": "Synthetic Agent Export",
                "messages": [
                    {"role": "user", "content": "ordinary chat should remain raw only"},
                    {"role": "assistant", "content": "Concept: Agent Export - JSON exports normalize into conversation turns."},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_cli("import-chat", str(source_path), "--out", str(out_path), "--source-id", "agent-json", "--title", "Agent Export")

    assert "Exported 2 turns" in result.stdout
    records = read_jsonl(out_path)
    assert [record["role"] for record in records] == ["user", "assistant"]
    assert all(record["source"] == "generic" for record in records)
    assert all(record["source_id"] == "agent-json" for record in records)
    assert all(record["conversation_id"] == "agent-json" for record in records)
    assert str(source_path) not in out_path.read_text(encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(out_path), "--ontology", str(ontology_dir), "--source-id", "agent-json")
    candidates = read_jsonl(ontology_dir / "review" / "pending.jsonl")
    assert len(candidates) == 1
    assert candidates[0]["label"] == "Agent Export"
    assert "ordinary chat should remain raw only" not in json.dumps(candidates, ensure_ascii=False)


def test_import_chat_codex_jsonl_skips_metadata_tool_events_and_can_ingest(tmp_path):
    source_path = tmp_path / "codex-session.jsonl"
    out_path = tmp_path / "codex-normalized.jsonl"
    ontology_dir = tmp_path / "ontology"
    private_marker = "/Users/synthetic/private-project"
    write_jsonl(
        source_path,
        [
            {"format": "codex.synthetic.jsonl.v0", "event": "session", "cwd": private_marker},
            {"format": "codex.synthetic.jsonl.v0", "event": "message", "role": "user", "content": [{"type": "input_text", "text": "Please convert useful notes only."}]},
            {
                "format": "codex.synthetic.jsonl.v0",
                "event": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Concept: Review Queue - Candidate records wait for explicit approval.\nMust: Do not compile raw transcripts directly.",
                    },
                    {"type": "cwd", "text": private_marker},
                ],
            },
            {"format": "codex.synthetic.jsonl.v0", "event": "tool_call", "command": f"cat {private_marker}/secret.txt"},
            {
                "format": "codex.synthetic.jsonl.v0",
                "event": "tool_call",
                "message": {"role": "assistant", "content": [{"type": "output_text", "text": f"Must: Nested Codex tool calls must not leak {private_marker}."}]},
            },
        ],
    )

    run_cli("import-chat", str(source_path), "--source", "codex", "--out", str(out_path), "--source-id", "codex-demo")

    normalized_text = out_path.read_text(encoding="utf-8")
    assert private_marker not in normalized_text
    assert "tool_call" not in normalized_text
    records = read_jsonl(out_path)
    assert [record["role"] for record in records] == ["user", "assistant"]
    assert all(record["source"] == "codex" for record in records)

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    result = run_cli("import-chat", str(source_path), "--source", "codex", "--ontology", str(ontology_dir), "--source-id", "codex-demo")

    assert "extracted 2 candidates" in result.stdout
    pending_text = (ontology_dir / "review" / "pending.jsonl").read_text(encoding="utf-8")
    candidates = read_jsonl(ontology_dir / "review" / "pending.jsonl")
    assert [candidate["kind"] for candidate in candidates] == ["concept", "rule"]
    assert private_marker not in pending_text
    assert all(ref["source_path"] == "raw/conversations/codex-demo.jsonl" for candidate in candidates for ref in candidate["source_refs"])


def test_import_chat_claude_code_jsonl_skips_tool_blocks(tmp_path):
    source_path = tmp_path / "claude-code-session.jsonl"
    ontology_dir = tmp_path / "ontology"
    private_marker = "/Users/synthetic/private-project"
    write_jsonl(
        source_path,
        [
            {"format": "claude-code.synthetic.jsonl.v0", "type": "summary", "summary": f"Synthetic summary {private_marker}"},
            {
                "format": "claude-code.synthetic.jsonl.v0",
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": "Please preserve only tagged lines."}]},
            },
            {
                "format": "claude-code.synthetic.jsonl.v0",
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Prefer: Keep importers deterministic and dependency-free."},
                        {"type": "tool_use", "input": {"path": f"{private_marker}/secret.txt"}},
                    ],
                },
            },
            {
                "format": "claude-code.synthetic.jsonl.v0",
                "type": "user",
                "message": {"role": "user", "content": [{"type": "tool_result", "content": f"tool output from {private_marker}"}]},
            },
        ],
    )

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    result = run_cli("import-chat", str(source_path), "--source", "claude-code", "--ontology", str(ontology_dir), "--source-id", "claude-demo")

    assert "extracted 1 candidates" in result.stdout
    raw_text = (ontology_dir / "raw" / "conversations" / "claude-demo.jsonl").read_text(encoding="utf-8")
    pending_text = (ontology_dir / "review" / "pending.jsonl").read_text(encoding="utf-8")
    raw_records = read_jsonl(ontology_dir / "raw" / "conversations" / "claude-demo.jsonl")
    candidates = read_jsonl(ontology_dir / "review" / "pending.jsonl")
    assert len(raw_records) == 2
    assert [record["role"] for record in raw_records] == ["user", "assistant"]
    assert candidates[0]["rule_type"] == "prefer"
    assert private_marker not in raw_text
    assert private_marker not in pending_text


def test_import_chat_generic_jsonl_skips_tool_metadata_records(tmp_path):
    source_path = tmp_path / "generic-agent-session.jsonl"
    out_path = tmp_path / "conversation.jsonl"
    private_marker = "/Users/synthetic/private-project"
    write_jsonl(
        source_path,
        [
            {"event": "tool_call", "message": f"cat {private_marker}/secret.txt"},
            {"event": "tool_call", "message": {"role": "assistant", "content": f"Must: Nested tool calls must not leak {private_marker}."}},
            {"type": "command", "content": f"open {private_marker}/notes.md"},
            {"type": "metadata", "content": f"cwd={private_marker}"},
            {"role": "tool", "content": f"tool output from {private_marker}"},
            {"role": "tool_result", "content": f"tool result from {private_marker}"},
            {"role": "assistant", "content": "Must: Generic import should skip tool metadata records."},
        ],
    )

    run_cli("import-chat", str(source_path), "--source", "generic", "--out", str(out_path), "--source-id", "generic-demo")

    normalized_text = out_path.read_text(encoding="utf-8")
    records = read_jsonl(out_path)
    assert len(records) == 1
    assert records[0]["text"] == "Must: Generic import should skip tool metadata records."
    assert private_marker not in normalized_text


def test_ontology_workflow_approve_all_tagged_ignores_stale_pending_candidates(tmp_path):
    work_dir = tmp_path / "workflow"
    ontology_dir = work_dir / "ontology"
    stale_path = tmp_path / "stale.md"
    current_path = tmp_path / "current.md"
    stale_marker = "/Users/synthetic/private-project"
    stale_path.write_text(f"Must: Stale pending candidate mentions {stale_marker}.\n", encoding="utf-8")
    current_path.write_text("Must: Current import candidates can be approved in one-command workflow.\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(stale_path), "--ontology", str(ontology_dir), "--source-id", "stale-chat")

    run_cli(
        "ontology-workflow",
        str(current_path),
        "--work-dir",
        str(work_dir),
        "--pack-id",
        "mindpack.test",
        "--title",
        "Test Ontology",
        "--question",
        "What should be approved?",
        "--source-id",
        "current-chat",
        "--approve-all-tagged",
    )

    pack_dir = work_dir / "pack"
    ontology_text = (pack_dir / "ontology.jsonl").read_text(encoding="utf-8")
    assert "Current import candidates can be approved" in ontology_text
    assert stale_marker not in ontology_text
    assert_pack_text_excludes(pack_dir, stale_marker)


def test_ontology_workflow_approve_all_tagged_ignores_stale_pending_candidates_with_reused_source_id(tmp_path):
    work_dir = tmp_path / "workflow"
    stale_path = tmp_path / "stale.md"
    current_path = tmp_path / "current.md"
    stale_marker = "/Users/synthetic/private-project"
    stale_path.write_text(f"Must: Stale same-source pending candidate mentions {stale_marker}.\n", encoding="utf-8")
    current_path.write_text("Must: Current same-source import is the only auto-approved candidate.\n", encoding="utf-8")

    run_cli(
        "ontology-workflow",
        str(stale_path),
        "--work-dir",
        str(work_dir),
        "--pack-id",
        "mindpack.test",
        "--title",
        "Test Ontology",
        "--question",
        "What should stay pending?",
        "--source-id",
        "shared-chat",
    )
    run_cli(
        "ontology-workflow",
        str(current_path),
        "--work-dir",
        str(work_dir),
        "--pack-id",
        "mindpack.test",
        "--title",
        "Test Ontology",
        "--question",
        "What should be approved?",
        "--source-id",
        "shared-chat",
        "--approve-all-tagged",
    )

    pack_dir = work_dir / "pack"
    ontology_text = (pack_dir / "ontology.jsonl").read_text(encoding="utf-8")
    assert "Current same-source import is the only auto-approved candidate" in ontology_text
    assert stale_marker not in ontology_text
    assert "Stale same-source pending candidate" not in ontology_text
    assert_pack_text_excludes(pack_dir, stale_marker)


def test_ontology_workflow_filters_stale_source_refs_for_duplicate_candidate_ids(tmp_path):
    work_dir = tmp_path / "workflow"
    ontology_dir = work_dir / "ontology"
    stale_path = tmp_path / "stale.md"
    current_path = tmp_path / "current.md"
    duplicate_statement = "Must: Duplicate candidate should keep current source refs only.\n"
    stale_path.write_text(duplicate_statement, encoding="utf-8")
    current_path.write_text(duplicate_statement, encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(stale_path), "--ontology", str(ontology_dir), "--source-id", "stale-chat")
    run_cli(
        "ontology-workflow",
        str(current_path),
        "--work-dir",
        str(work_dir),
        "--pack-id",
        "mindpack.test",
        "--title",
        "Test Ontology",
        "--question",
        "What should be approved?",
        "--source-id",
        "current-chat",
        "--approve-all-tagged",
    )

    ontology_text = (work_dir / "pack" / "ontology.jsonl").read_text(encoding="utf-8")
    assert "current-chat" in ontology_text
    assert "raw/conversations/current-chat.jsonl" in ontology_text
    assert "stale-chat" not in ontology_text
    assert "raw/conversations/stale-chat.jsonl" not in ontology_text


def test_approve_candidates_all_approves_pending_candidates(tmp_path):
    ontology_dir = tmp_path / "ontology"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text(
        "Concept: Review Queue - Candidate records wait for approval.\n"
        "Must: Approved ontology should include only reviewed tagged lines.\n"
        "raw untagged sentence should not become ontology.\n",
        encoding="utf-8",
    )

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    result = run_cli("approve-candidates", str(ontology_dir), "--all")

    assert "Approved 2 candidates" in result.stdout
    approved = read_jsonl(ontology_dir / "ontology" / "approved.jsonl")
    assert len(approved) == 2
    assert all(record["status"] == "approved" for record in approved)
    assert "raw untagged sentence" not in json.dumps(approved, ensure_ascii=False)


def test_ontology_workflow_one_command_writes_valid_pack_and_runtime_context(tmp_path):
    conversation_path = tmp_path / "conversation.md"
    work_dir = tmp_path / "workflow"
    raw_private_sentence = "This private raw sentence should never appear in compiled output."
    conversation_path.write_text(
        "Concept: Agent Chat Import - Agent conversations can become reviewed ontology candidates.\n"
        "Prefer: Keep raw transcripts local and compile only approved ontology entries.\n"
        f"{raw_private_sentence}\n",
        encoding="utf-8",
    )

    result = run_cli(
        "ontology-workflow",
        str(conversation_path),
        "--work-dir",
        str(work_dir),
        "--pack-id",
        "mindpack.test",
        "--title",
        "Test Ontology",
        "--question",
        "How should raw chats be handled?",
        "--approve-all-tagged",
    )

    assert "VALID" in result.stdout
    pack_dir = work_dir / "pack"
    context_path = pack_dir / "samples" / "runtime_context.md"
    assert (pack_dir / "mindpack.yaml").is_file()
    assert context_path.is_file()
    context = context_path.read_text(encoding="utf-8")
    assert "## Selected Ontology" in context
    assert "Agent Chat Import" in context
    assert "Keep raw transcripts local" in context
    assert raw_private_sentence not in context
    assert_pack_text_excludes(pack_dir, raw_private_sentence)
    assert_public_text_is_sanitized(pack_dir)


def test_ontology_workflow_help_describes_review_gate_and_safe_one_command_use():
    result = run_cli("ontology-workflow", "--help")

    assert "--approve-all-tagged" in result.stdout
    assert "synthetic or already-" in result.stdout
    assert "reviewed exports" in result.stdout


def test_ontology_workflow_without_approve_all_stops_before_compile(tmp_path):
    conversation_path = tmp_path / "conversation.md"
    work_dir = tmp_path / "workflow"
    conversation_path.write_text("Must: Stop before compile until candidates are approved.\n", encoding="utf-8")

    result = run_cli(
        "ontology-workflow",
        str(conversation_path),
        "--work-dir",
        str(work_dir),
        "--pack-id",
        "mindpack.test",
        "--title",
        "Test Ontology",
        "--question",
        "How should raw chats be handled?",
    )

    assert "Review pending candidates" in result.stdout
    assert (work_dir / "ontology" / "review" / "pending.jsonl").is_file()
    assert not (work_dir / "pack" / "mindpack.yaml").exists()
