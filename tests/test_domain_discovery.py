import json
from pathlib import Path

from test_mindpack_kit import read_jsonl, run_cli


def test_discover_domains_finds_operator_multi_domain_registry(tmp_path):
    source = tmp_path / "operator-ai-history.md"
    source.write_text(
        """
        User-visible outputs should be Korean, accuracy first, and plans should come before execution.
        수익형 아이디어는 실제 시장 pain, paid willingness, 5~7h/week feasibility, 영어 부담을 기준으로 본다.
        일반 앱 아이디어와 수익형 후보는 PRD, 우선순위, MVP 범위, 검증 기준을 먼저 정리한다.

        korea_stock Agent Judge와 my-stock-scanner는 후보별 리서치, BUY/WATCH/REJECT 판단, paper trade, TP/SL,
        D+1 시가, Telegram compact 카드, portfolio cron의 최대 1종목 실제 매수 추천 제한을 다룬다.
        개인 포트폴리오 크론은 실제 매수/추가매수 추천은 최대 1종목, 나머지는 관찰 후보로 둔다.

        AI Foundation은 Slack 중심이고 Orchestrator가 expert/exec/gates subagent를 배분한다.
        Codex 작업은 tmux에서 보이게 실행하고, worker는 관리자 ACK 없이 다음 작업을 진행하지 않는다.

        Mindpack은 GitHub public repo, fork, pull request, issue template, branch protection, README, OSS traffic,
        portable context pack, ontology registry, domain discovery, sample pack, adapter 생태계로 제품화한다.

        GEO, AI Search, 마케팅 리드수집, site-native intake, Airtable intake를 우선순위로 둔다.
        Threads 리서치/댓글은 쉼표보다 느낌표를 선호하고, 올드한 표현은 피한다.
        뉴스 브리핑은 확장 요약과 링크를 항상 포함한다.
        """.strip(),
        encoding="utf-8",
    )
    out_dir = tmp_path / "domain-registry"

    result = run_cli("discover-domains", str(source), "--out", str(out_dir))

    assert "Discovered" in result.stdout
    registry = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    active_ids = {domain["id"] for domain in registry["domains"] if domain["status"] == "active"}
    assert {
        "core-user-profile",
        "idea-evaluator",
        "stock-research-judge",
        "portfolio-management",
        "ai-agent-ops",
        "oss-product-strategy",
        "marketing-growth",
        "content-tone-memory",
        "news-research-briefing",
    }.issubset(active_ids)
    assert len(active_ids) >= 9
    assert active_ids != {"idea-evaluator"}

    manifest = read_jsonl(out_dir / "domain_manifest.jsonl")
    assert [domain["id"] for domain in manifest] == [domain["id"] for domain in registry["domains"]]

    assignments = read_jsonl(out_dir / "source_assignments.jsonl")
    assert len(assignments) == 1
    assigned_ids = {domain["id"] for domain in assignments[0]["domains"]}
    assert "stock-research-judge" in assigned_ids
    assert "oss-product-strategy" in assigned_ids
    assert "idea-evaluator" in assigned_ids

    assert (out_dir / "domains" / "stock-research-judge" / "README.md").is_file()
    assert (out_dir / "domains" / "oss-product-strategy" / "README.md").is_file()
    report = (out_dir / "domain_coverage_report.md").read_text(encoding="utf-8")
    assert "stock-research-judge" in report
    assert "oss-product-strategy" in report
    assert "아이디어 도메인 하나로 압축하지 않음" in report


def test_discover_domains_keeps_unmatched_sources_unassigned(tmp_path):
    source = tmp_path / "unrelated.md"
    source.write_text(
        "A small note about watering balcony herbs and choosing ceramic pots.",
        encoding="utf-8",
    )
    out_dir = tmp_path / "domain-registry"

    run_cli("discover-domains", str(source), "--out", str(out_dir))

    registry = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    assert registry["domains"] == []
    unassigned = read_jsonl(out_dir / "unassigned_sources.jsonl")
    assert len(unassigned) == 1
    assert unassigned[0]["source_id"].startswith("source-")
    assert unassigned[0]["path"].endswith("unrelated.md")


def test_discover_domains_ignores_generic_single_keyword_noise(tmp_path):
    source = tmp_path / "generic-noise.md"
    source.write_text(
        "The garden plan has a short summary, a README draft, a lead-free glaze, and a warm tone.",
        encoding="utf-8",
    )
    out_dir = tmp_path / "domain-registry"

    run_cli("discover-domains", str(source), "--out", str(out_dir))

    registry = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    assert registry["domains"] == []
    unassigned = read_jsonl(out_dir / "unassigned_sources.jsonl")
    assert len(unassigned) == 1


def test_discover_domains_does_not_double_count_overlapping_keyword_signals(tmp_path):
    cases = {
        "slack-only.md": "Slack is where this note lives.",
        "paid-willingness-only.md": "Paid willingness matters, but this note has no other idea-evaluation criteria.",
    }
    for filename, text in cases.items():
        source = tmp_path / filename
        source.write_text(text, encoding="utf-8")
        out_dir = tmp_path / f"registry-{source.stem}"

        run_cli("discover-domains", str(source), "--out", str(out_dir))

        registry = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
        assert registry["domains"] == [], filename
        assert len(read_jsonl(out_dir / "unassigned_sources.jsonl")) == 1


def test_discover_domains_counts_later_independent_subphrase_signal(tmp_path):
    source = tmp_path / "idea-evidence.md"
    source.write_text(
        "Paid willingness appears in the interview, and later willingness appears as a separate buying signal.",
        encoding="utf-8",
    )
    out_dir = tmp_path / "domain-registry"

    run_cli("discover-domains", str(source), "--out", str(out_dir))

    registry = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    assert {domain["id"] for domain in registry["domains"]} == {"idea-evaluator"}
    idea_domain = registry["domains"][0]
    assert "paid willingness" in idea_domain["matched_keywords"]
    assert "willingness" in idea_domain["matched_keywords"]


def test_discover_domains_rejects_output_equal_to_or_above_source_root(tmp_path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "criteria.md").write_text("Mindpack GitHub public repo README OSS traffic.", encoding="utf-8")

    same_dir = run_cli("discover-domains", str(source_root), "--out", str(source_root), check=False)
    assert same_dir.returncode != 0
    assert "output directory cannot be equal to or contain a source path" in same_dir.stderr

    parent_dir = run_cli("discover-domains", str(source_root), "--out", str(tmp_path), check=False)
    assert parent_dir.returncode != 0
    assert "output directory cannot be equal to or contain a source path" in parent_dir.stderr


def test_discover_domains_rerun_skips_nested_output_and_removes_stale_domain_dirs(tmp_path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "criteria.md"
    source.write_text(
        "Mindpack GitHub public repo, fork, pull request, issue template, README, OSS traffic, "
        "ontology registry, domain discovery, sample pack, adapter strategy.",
        encoding="utf-8",
    )
    out_dir = source_root / "domain-registry"

    run_cli("discover-domains", str(source_root), "--out", str(out_dir))
    first_registry = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    assert first_registry["source_count"] == 1
    assert {domain["id"] for domain in first_registry["domains"]} == {"oss-product-strategy"}
    assert (out_dir / "domains" / "oss-product-strategy" / "README.md").is_file()

    source.write_text("A small note about watering balcony herbs and choosing ceramic pots.", encoding="utf-8")
    run_cli("discover-domains", str(source_root), "--out", str(out_dir))

    second_registry = json.loads((out_dir / "registry.json").read_text(encoding="utf-8"))
    assert second_registry["source_count"] == 1
    assert second_registry["domains"] == []
    assert read_jsonl(out_dir / "domain_manifest.jsonl") == []
    assert read_jsonl(out_dir / "source_assignments.jsonl") == []
    assert len(read_jsonl(out_dir / "unassigned_sources.jsonl")) == 1
    assert not (out_dir / "domains" / "oss-product-strategy").exists()
