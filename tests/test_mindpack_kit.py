import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE = "founder-idea-evaluator"
PACK_ID = "mindpack.founder-idea-evaluator"
TITLE = "Founder Idea Evaluator"
LEGACY_PERSONAL_MARKER = "se" + "ok"
PRIVATE_PATH_MARKERS = [str(PROJECT_ROOT), "/Users/", "Desktop/", "/workspace/"]
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}


def run_cli(*args, cwd=PROJECT_ROOT, check=True):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        ["python3", "-m", "mindpack_kit", *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(args)}\n"
            f"exit={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name in {"README", "LICENSE"}):
            yield path


def assert_public_text_is_sanitized(root: Path):
    for path in iter_text_files(root):
        relative_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert LEGACY_PERSONAL_MARKER not in relative_path.casefold(), relative_path
        assert LEGACY_PERSONAL_MARKER not in text.casefold(), relative_path
        for marker in PRIVATE_PATH_MARKERS:
            assert marker not in text, relative_path


def compile_founder_pack(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    pack_dir = tmp_path / "pack"
    run_cli("init-wiki", "--out", str(wiki_dir), "--profile", PROFILE)
    run_cli("compile", str(wiki_dir), "--out", str(pack_dir), "--pack-id", PACK_ID, "--title", TITLE)
    return wiki_dir, pack_dir


def test_init_wiki_creates_expected_source_structure(tmp_path):
    wiki_dir = tmp_path / "wiki"

    run_cli("init-wiki", "--out", str(wiki_dir), "--profile", PROFILE)

    expected_paths = [
        "SCHEMA.md",
        "index.md",
        "log.md",
        "personas/founder-idea-evaluator.md",
        "concepts/market-validation.md",
        "concepts/feasibility-filters.md",
        "concepts/idea-shortlist.md",
        "rules/commerce-validation.md",
        "rules/rejection-filters.md",
        "rules/preference-heuristics.md",
        "evaluations/idea-evaluation-rubric.md",
        "raw/notes/founder-criteria.md",
    ]
    for relative_path in expected_paths:
        assert (wiki_dir / relative_path).is_file(), relative_path

    criteria_note = (wiki_dir / "raw/notes/founder-criteria.md").read_text(encoding="utf-8")
    assert "deep research before selecting monetizable ideas" in criteria_note
    assert "willingness-to-pay pain" in criteria_note
    assert "limited founder bandwidth" in criteria_note
    assert "strict commerce validation" in criteria_note
    assert_public_text_is_sanitized(wiki_dir)


def test_compile_emits_required_mindpack_files(tmp_path):
    _, pack_dir = compile_founder_pack(tmp_path)

    for relative_path in [
        "mindpack.yaml",
        "graph.jsonl",
        "rules.json",
        "persona.yaml",
        "provenance.json",
        "evals.json",
        "ontology.jsonl",
        "samples/runtime_context.md",
        "quality_report.json",
        "README.md",
    ]:
        assert (pack_dir / relative_path).is_file(), relative_path

    mindpack = (pack_dir / "mindpack.yaml").read_text(encoding="utf-8")
    assert f"id: {PACK_ID}" in mindpack
    assert f"title: {TITLE}" in mindpack


def test_compile_extracts_wikilink_graph_edges(tmp_path):
    wiki_dir = tmp_path / "wiki"
    (wiki_dir / "concepts").mkdir(parents=True)
    (wiki_dir / "index.md").write_text(
        "---\ntitle: Home\ntags: [entry]\n---\n\nSee [[concepts/market-pain]] and [[Market Pain|the pain]].\n",
        encoding="utf-8",
    )
    (wiki_dir / "concepts/market-pain.md").write_text(
        "---\ntitle: Market Pain\ntags:\n  - concept\n---\n\nMarket pain node.\n",
        encoding="utf-8",
    )
    pack_dir = tmp_path / "pack"

    run_cli("compile", str(wiki_dir), "--out", str(pack_dir), "--pack-id", "test.pack", "--title", "Test Pack")

    records = read_jsonl(pack_dir / "graph.jsonl")
    nodes = [record for record in records if record["record_type"] == "node"]
    edges = [record for record in records if record["record_type"] == "edge"]
    assert {node["id"] for node in nodes} == {"index", "concepts/market-pain"}
    node_ids = {node["id"] for node in nodes}
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in edges)
    assert sum(edge["source"] == "index" and edge["target"] == "concepts/market-pain" for edge in edges) == 1


def test_compile_ignores_code_wikilinks_raw_links_and_keeps_edges_resolved(tmp_path):
    wiki_dir = tmp_path / "wiki"
    (wiki_dir / "concepts").mkdir(parents=True)
    (wiki_dir / "index.md").write_text(
        "---\ntitle: Home\ntags: [entry]\n---\n\n"
        "Valid path [[concepts/market-pain]] and title [[Market Pain|pain]].\n"
        "Raw notes [[raw/notes/private-source]] should stay out of the graph.\n"
        "Inline code `[[concepts/code-only]]` should not become an edge.\n\n"
        "```markdown\n[[concepts/block-only]]\n```\n",
        encoding="utf-8",
    )
    for stem, title in [
        ("market-pain", "Market Pain"),
        ("code-only", "Code Only"),
        ("block-only", "Block Only"),
    ]:
        (wiki_dir / f"concepts/{stem}.md").write_text(
            f"---\ntitle: {title}\ntags: [concept]\n---\n\n# {title}\n",
            encoding="utf-8",
        )
    pack_dir = tmp_path / "pack"

    run_cli("compile", str(wiki_dir), "--out", str(pack_dir), "--pack-id", "test.pack", "--title", "Test Pack")

    records = read_jsonl(pack_dir / "graph.jsonl")
    nodes = [record for record in records if record["record_type"] == "node"]
    edges = [record for record in records if record["record_type"] == "edge"]
    node_ids = {node["id"] for node in nodes}
    edge_targets = {edge["target"] for edge in edges}

    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in edges)
    assert edge_targets == {"concepts/market-pain"}
    assert "raw/notes/private-source" not in edge_targets
    assert "concepts/code-only" not in edge_targets
    assert "concepts/block-only" not in edge_targets


def test_validate_rejects_unresolved_graph_edge_targets(tmp_path):
    _, pack_dir = compile_founder_pack(tmp_path)
    graph_path = pack_dir / "graph.jsonl"
    with graph_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"record_type": "edge", "source": "index", "target": "missing-node", "label": "wikilink"}) + "\n")

    result = run_cli("validate", str(pack_dir), check=False)

    assert result.returncode != 0
    assert "INVALID" in result.stdout
    assert "unresolved graph edge target" in result.stdout
    assert "missing-node" in result.stdout


def test_validate_rejects_missing_required_files(tmp_path):
    pack_dir = tmp_path / "broken-pack"
    pack_dir.mkdir()
    (pack_dir / "mindpack.yaml").write_text("id: broken\n", encoding="utf-8")

    result = run_cli("validate", str(pack_dir), check=False)

    assert result.returncode != 0
    assert "INVALID" in result.stdout
    assert "missing" in result.stdout.lower()


def test_run_creates_runtime_context_with_rules_and_citations(tmp_path):
    _, pack_dir = compile_founder_pack(tmp_path)
    context_path = pack_dir / "samples" / "runtime_context.md"
    question = "Should this idea continue after strict commerce validation?"

    run_cli("run", str(pack_dir), "--question", question, "--out", str(context_path))

    context = context_path.read_text(encoding="utf-8")
    assert f"# Runtime Context: {TITLE}" in context
    assert "## System Instructions" in context
    assert "## Primary Persona" in context
    assert "You are the Founder Idea Evaluator" in context
    assert "## User Question" in context
    assert "untrusted" in context.lower()
    assert f"```text\n{question}\n```" in context
    assert "- Question:" not in context
    assert "## Selected Rules" in context
    assert "strict commerce validation" in context
    assert "## Citations" in context
    assert "rules/commerce-validation.md" in context
    assert "SCHEMA.md" not in context
    assert "log.md" not in context


def test_compile_cleans_stale_output_files(tmp_path):
    wiki_dir = tmp_path / "wiki"
    pack_dir = tmp_path / "pack"
    stale_path = pack_dir / "samples" / "runtime_context_parent_verify.md"
    stale_path.parent.mkdir(parents=True)
    stale_path.write_text("stale", encoding="utf-8")
    run_cli("init-wiki", "--out", str(wiki_dir), "--profile", PROFILE)

    run_cli("compile", str(wiki_dir), "--out", str(pack_dir), "--pack-id", PACK_ID, "--title", TITLE)

    assert not stale_path.exists()
    assert (pack_dir / "samples" / "runtime_context.md").is_file()


def test_provenance_uses_relative_source_label_without_absolute_paths(tmp_path):
    wiki_dir, pack_dir = compile_founder_pack(tmp_path)

    provenance_text = (pack_dir / "provenance.json").read_text(encoding="utf-8")
    provenance = json.loads(provenance_text)
    assert str(wiki_dir.resolve()) not in provenance_text
    assert str(PROJECT_ROOT) not in provenance_text
    assert provenance["source_root"] == wiki_dir.name
    assert all(not Path(page["source_path"]).is_absolute() for page in provenance["compiled_pages"])


def test_generated_pack_output_is_public_sanitized(tmp_path):
    _, pack_dir = compile_founder_pack(tmp_path)

    assert_public_text_is_sanitized(pack_dir)


def test_public_example_sources_are_sanitized():
    examples_dir = PROJECT_ROOT / "examples"
    founder_example = examples_dir / "founder-idea-wiki"

    assert founder_example.is_dir()
    assert_public_text_is_sanitized(examples_dir)
