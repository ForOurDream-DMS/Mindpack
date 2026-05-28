import json
from pathlib import Path

from test_mindpack_kit import PROJECT_ROOT, assert_public_text_is_sanitized, read_jsonl, run_cli


TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}


def write_jsonl(path: Path, records):
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def assert_pack_text_excludes(pack_dir: Path, forbidden: str):
    for path in pack_dir.rglob("*"):
        if path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name in {"README", "LICENSE"}):
            assert forbidden not in path.read_text(encoding="utf-8", errors="ignore"), path.relative_to(pack_dir).as_posix()


def test_ingest_conversation_extracts_pending_candidates_from_tagged_lines(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text(
        "User: ordinary chat should stay raw only.\n"
        "Concept: Candidate Review Queue - Proposed knowledge must be reviewed before it becomes ontology.\n"
        "Must: Do not merge raw LLM conversations directly into the approved ontology.\n"
        "Prefer: Keep the canonical ontology file-first and git-friendly.\n"
        "Assistant: this untagged private-looking sentence should not become a candidate.\n",
        encoding="utf-8",
    )

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    result = run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")

    pending_path = ontology_dir / "review" / "pending.jsonl"
    raw_path = ontology_dir / "raw" / "conversations" / "demo-chat.jsonl"
    assert pending_path.is_file()
    assert raw_path.is_file()
    assert "3 candidates" in result.stdout

    candidates = read_jsonl(pending_path)
    assert [candidate["kind"] for candidate in candidates] == ["concept", "rule", "rule"]
    assert candidates[0]["label"] == "Candidate Review Queue"
    assert candidates[1]["rule_type"] == "must"
    assert candidates[2]["rule_type"] == "prefer"
    assert all(candidate["status"] == "pending" for candidate in candidates)
    assert all(not Path(ref["source_path"]).is_absolute() for candidate in candidates for ref in candidate["source_refs"])
    assert "ordinary chat should stay raw only" not in json.dumps(candidates, ensure_ascii=False)
    assert str(conversation_path) not in pending_path.read_text(encoding="utf-8")


def test_approve_compile_and_run_use_only_approved_ontology_entries(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text(
        "Concept: Review Queue - Candidate records wait for explicit approval.\n"
        "Must: Approved ontology must exclude raw conversation transcripts.\n"
        "Prefer: Runtime context should include approved ontology statements.\n"
        "This raw sentence should never appear in the compiled runtime context.\n",
        encoding="utf-8",
    )

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidates = read_jsonl(ontology_dir / "review" / "pending.jsonl")
    accepted_ids = [candidates[0]["id"], candidates[1]["id"]]

    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", accepted_ids[0], "--candidate-id", accepted_ids[1])
    run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("validate", str(pack_dir))

    ontology_records = read_jsonl(pack_dir / "ontology.jsonl")
    assert [record["id"] for record in ontology_records] == ["ont_" + accepted_ids[0][5:], "ont_" + accepted_ids[1][5:]]
    assert "Runtime context should include approved ontology statements" not in json.dumps(ontology_records, ensure_ascii=False)

    context = run_cli("run", str(pack_dir), "--question", "How should approved ontology handle raw conversations?").stdout
    assert "## Selected Ontology" in context
    assert "Review Queue" in context
    assert "Approved ontology must exclude raw conversation transcripts" in context
    assert "This raw sentence should never appear" not in context
    assert_pack_text_excludes(pack_dir, "This raw sentence should never appear")
    assert_public_text_is_sanitized(pack_dir)


def test_validate_rejects_absolute_ontology_source_paths(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Must: Ontology source references must stay relative.\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidate = read_jsonl(ontology_dir / "review" / "pending.jsonl")[0]
    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", candidate["id"])
    run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")

    for unsafe_path in [
        "/absolute/private-chat.jsonl",
        "../private-chat.jsonl",
        "raw/../private-chat.jsonl",
        "raw/%2e%2e/private-chat.jsonl",
        "raw/%252e%252e/private-chat.jsonl",
        "C:/Private/chat.jsonl",
        "C:\\Private\\chat.jsonl",
        "file:/private/chat.jsonl",
        "file:///private/chat.jsonl",
        "https://example.invalid/chat.jsonl",
        "~/private-chat.jsonl",
        "//server/share/chat.jsonl",
    ]:
        ontology_path = pack_dir / "ontology.jsonl"
        records = read_jsonl(ontology_path)
        records[0]["source_refs"][0]["source_path"] = unsafe_path
        write_jsonl(ontology_path, records)

        result = run_cli("validate", str(pack_dir), check=False)

        assert result.returncode != 0, unsafe_path
        assert "INVALID" in result.stdout
        assert "unsafe ontology source path" in result.stdout


def test_validate_rejects_unsafe_provenance_source_paths(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Must: Provenance source references must stay relative.\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidate = read_jsonl(ontology_dir / "review" / "pending.jsonl")[0]
    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", candidate["id"])
    run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")

    provenance_path = pack_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["compiled_pages"][0]["source_path"] = "/absolute/private-chat.jsonl"
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = run_cli("validate", str(pack_dir), check=False)

    assert result.returncode != 0
    assert "INVALID" in result.stdout
    assert "unsafe provenance source path" in result.stdout


def test_multiline_jsonl_content_extracts_each_tagged_line(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    conversation_path = tmp_path / "conversation.jsonl"
    conversation_path.write_text(
        json.dumps(
            {
                "role": "assistant",
                "content": "Intro line.\nConcept: Multi-line Import - Tagged lines inside one message are extracted.\nMust: Scan each line inside exported chat turns.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "jsonl-chat")

    candidates = read_jsonl(ontology_dir / "review" / "pending.jsonl")
    assert [candidate["kind"] for candidate in candidates] == ["concept", "rule"]
    assert candidates[0]["label"] == "Multi-line Import"
    assert candidates[1]["statement"] == "Scan each line inside exported chat turns."


def test_compile_rejects_unsafe_approved_source_refs_before_touching_output(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Must: Approved source references must stay relative.\n", encoding="utf-8")
    pack_dir.mkdir()
    sentinel = pack_dir / "keep.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidate = read_jsonl(ontology_dir / "review" / "pending.jsonl")[0]
    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", candidate["id"])
    approved_path = ontology_dir / "ontology" / "approved.jsonl"
    approved = read_jsonl(approved_path)
    approved[0]["source_refs"][0]["source_path"] = "/absolute/private-chat.jsonl"
    write_jsonl(approved_path, approved)

    result = run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology", check=False)

    assert result.returncode != 0
    assert "unsafe ontology source path" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep me"
    assert not (pack_dir / "mindpack.yaml").exists()


def test_compile_refuses_non_mindpack_output_dir(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Must: Compilers should not delete arbitrary non-Mindpack directories.\n", encoding="utf-8")
    pack_dir.mkdir()
    sentinel = pack_dir / "keep.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidate = read_jsonl(ontology_dir / "review" / "pending.jsonl")[0]
    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", candidate["id"])

    result = run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology", check=False)

    assert result.returncode != 0
    assert "does not look like generated Mindpack output" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep me"


def test_compile_can_replace_existing_generated_mindpack_output(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Must: Regenerating a Mindpack output directory should be allowed.\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidate = read_jsonl(ontology_dir / "review" / "pending.jsonl")[0]
    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", candidate["id"])
    run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    stale_file = pack_dir / "stale.txt"
    stale_file.write_text("stale generated byproduct", encoding="utf-8")

    run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")

    assert not stale_file.exists()
    run_cli("validate", str(pack_dir))


def test_compile_ontology_requires_at_least_one_approved_entry(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Concept: Pending Only - This candidate has not been approved yet.\n", encoding="utf-8")
    pack_dir.mkdir()
    sentinel = pack_dir / "keep.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")

    result = run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology", check=False)

    assert result.returncode != 0
    assert "no approved ontology entries" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep me"
    assert not (pack_dir / "mindpack.yaml").exists()


def test_concept_only_ontology_pack_validates(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    pack_dir = tmp_path / "pack"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Concept: Concept Only - Ontology packs do not require a rule entry.\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidate = read_jsonl(ontology_dir / "review" / "pending.jsonl")[0]
    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", candidate["id"])
    run_cli("compile-ontology", str(ontology_dir), "--out", str(pack_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")

    result = run_cli("validate", str(pack_dir), check=False)

    assert result.returncode == 0
    assert "VALID" in result.stdout


def test_compile_ontology_rejects_output_inside_workspace(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    conversation_path = tmp_path / "conversation.md"
    conversation_path.write_text("Must: Do not write compiled output inside the source workspace.\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir), "--source-id", "demo-chat")
    candidate = read_jsonl(ontology_dir / "review" / "pending.jsonl")[0]
    run_cli("approve-candidates", str(ontology_dir), "--candidate-id", candidate["id"])

    result = run_cli("compile-ontology", str(ontology_dir), "--out", str(ontology_dir / "pack"), "--pack-id", "mindpack.test", "--title", "Test Ontology", check=False)

    assert result.returncode != 0
    assert "refusing to clean out_dir" in result.stderr
    assert (ontology_dir / "ontology" / "approved.jsonl").is_file()


def test_init_ontology_preserves_existing_approved_records(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    approved_path = ontology_dir / "ontology" / "approved.jsonl"
    approved_path.write_text(json.dumps({"record_type": "ontology_entry", "id": "ont_keep", "kind": "claim", "label": "Keep", "statement": "Do not overwrite approved entries.", "status": "approved"}) + "\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")

    assert "ont_keep" in approved_path.read_text(encoding="utf-8")


def test_default_source_id_does_not_expose_sensitive_filename(tmp_path):
    ontology_dir = tmp_path / "ontology-workspace"
    conversation_path = tmp_path / "client-confidential-chat-2026-05-28.md"
    conversation_path.write_text("Must: Source identifiers should be non-identifying by default.\n", encoding="utf-8")

    run_cli("init-ontology", "--out", str(ontology_dir), "--pack-id", "mindpack.test", "--title", "Test Ontology")
    run_cli("ingest-conversation", str(conversation_path), "--ontology", str(ontology_dir))

    pending_text = (ontology_dir / "review" / "pending.jsonl").read_text(encoding="utf-8")
    raw_files = [path.name for path in (ontology_dir / "raw" / "conversations").iterdir()]
    assert "client" not in pending_text
    assert "confidential" not in pending_text
    assert all("client" not in name and "confidential" not in name for name in raw_files)
