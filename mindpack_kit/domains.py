"""Deterministic source-to-domain discovery for Mindpack registries.

This module intentionally uses only local keyword heuristics. It is a scaffold for
turning mixed AI-memory/source folders into multiple explicit Mindpack domains
without collapsing everything into one generic idea-evaluation pack.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from . import __version__

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}
GENERATED_MARKER = ".mindpack-domain-registry-generated"


@dataclass(frozen=True)
class DomainDefinition:
    id: str
    title: str
    summary: str
    keywords: tuple[str, ...]
    min_score: int = 2


DOMAIN_DEFINITIONS: tuple[DomainDefinition, ...] = (
    DomainDefinition(
        id="core-user-profile",
        title="Core User Profile",
        summary="Durable communication, language, planning, and quality preferences.",
        keywords=(
            "user-visible",
            "사용자 가시",
            "korean",
            "한국어",
            "accuracy",
            "정확성",
            "plan",
            "계획",
            "plans should come before execution",
            "중간공유",
        ),
    ),
    DomainDefinition(
        id="idea-evaluator",
        title="Idea Evaluator",
        summary="Market pain, willingness-to-pay, feasibility, PRD, MVP, and validation criteria.",
        keywords=(
            "수익형 아이디어",
            "아이디어",
            "market pain",
            "paid willingness",
            "willingness",
            "5~7h",
            "feasibility",
            "영어",
            "prd",
            "mvp",
            "검증",
            "우선순위",
        ),
    ),
    DomainDefinition(
        id="stock-research-judge",
        title="Stock Research Judge",
        summary="Single-stock research, agent judge decisions, paper trades, TP/SL, and trading notifications.",
        keywords=(
            "korea_stock",
            "my-stock-scanner",
            "agent judge",
            "buy/watch/reject",
            "paper trade",
            "tp/sl",
            "d+1",
            "telegram compact",
            "후보별 리서치",
            "판단",
            "매매",
        ),
    ),
    DomainDefinition(
        id="portfolio-management",
        title="Portfolio Management",
        summary="Portfolio cron rules, buy/add recommendations, observation candidates, and allocation discipline.",
        keywords=(
            "portfolio cron",
            "포트폴리오",
            "최대 1종목",
            "추가매수",
            "실제 매수",
            "관찰 후보",
            "대체 후보",
            "allocation",
        ),
    ),
    DomainDefinition(
        id="ai-agent-ops",
        title="AI Agent Operations",
        summary="Slack-centered orchestration, subagents, Codex, tmux, gates, and worker protocols.",
        keywords=(
            "ai foundation",
            "slack",
            "orchestrator",
            "subagent",
            "expert/exec/gates",
            "codex",
            "tmux",
            "ack",
            "worker",
            "관리자",
        ),
    ),
    DomainDefinition(
        id="oss-product-strategy",
        title="OSS Product Strategy",
        summary="Public repository positioning, contribution flow, README, adapters, and GitHub traffic loops.",
        keywords=(
            "mindpack",
            "github",
            "public repo",
            "fork",
            "pull request",
            "issue template",
            "branch protection",
            "readme",
            "oss traffic",
            "portable context pack",
            "ontology registry",
            "domain discovery",
            "sample pack",
            "adapter",
            "제품화",
        ),
    ),
    DomainDefinition(
        id="marketing-growth",
        title="Marketing Growth",
        summary="GEO, AI search, lead capture, intake flows, Airtable, and acquisition priority.",
        keywords=(
            "geo",
            "ai search",
            "마케팅",
            "리드수집",
            "lead",
            "site-native intake",
            "airtable",
            "intake",
            "우선순위",
        ),
    ),
    DomainDefinition(
        id="content-tone-memory",
        title="Content Tone Memory",
        summary="Reusable tone preferences for social writing, comments, and phrasing constraints.",
        keywords=(
            "threads",
            "댓글",
            "쉼표",
            "느낌표",
            "올드한 표현",
            "어투",
            "tone",
            "표현",
        ),
    ),
    DomainDefinition(
        id="news-research-briefing",
        title="News Research Briefing",
        summary="News briefing format, expanded summaries, links, and research-note presentation.",
        keywords=(
            "뉴스",
            "브리핑",
            "확장 요약",
            "링크",
            "research briefing",
            "briefing",
            "summary",
        ),
    ),
)


def discover_domains(source_paths: Sequence[str | Path], out_dir: str | Path) -> Dict[str, Any]:
    """Classify text sources into deterministic domain registry artifacts."""
    out_root = Path(out_dir)
    validate_output_layout(source_paths, out_root)
    sources = load_sources(source_paths, exclude_roots=[out_root])
    assignments: List[Dict[str, Any]] = []
    unassigned: List[Dict[str, Any]] = []
    domain_hits: Dict[str, Dict[str, Any]] = {}

    for source in sources:
        domains = classify_text(source["text"])
        if domains:
            assignment = {
                "record_type": "source_assignment",
                "source_id": source["source_id"],
                "path": source["display_path"],
                "sha256": source["sha256"],
                "domains": domains,
            }
            assignments.append(assignment)
            for domain in domains:
                hit = domain_hits.setdefault(
                    domain["id"],
                    {
                        "source_count": 0,
                        "score": 0,
                        "matched_keywords": [],
                    },
                )
                hit["source_count"] += 1
                hit["score"] += int(domain["score"])
                hit["matched_keywords"] = sorted(set(hit["matched_keywords"]) | set(domain["matched_keywords"]))
        else:
            unassigned.append(
                {
                    "record_type": "unassigned_source",
                    "source_id": source["source_id"],
                    "path": source["display_path"],
                    "sha256": source["sha256"],
                    "reason": "no known domain keyword matched",
                }
            )

    registry_domains = [domain_record(definition, domain_hits[definition.id]) for definition in DOMAIN_DEFINITIONS if definition.id in domain_hits]
    registry = {
        "record_type": "domain_registry",
        "format": "mindpack.domain-registry.v0",
        "version": __version__,
        "source_count": len(sources),
        "assigned_source_count": len(assignments),
        "unassigned_source_count": len(unassigned),
        "domains": registry_domains,
    }

    write_domain_artifacts(out_root, registry, assignments, unassigned)
    return {
        "source_count": len(sources),
        "domain_count": len(registry_domains),
        "assigned_source_count": len(assignments),
        "unassigned_source_count": len(unassigned),
        "registry_path": "registry.json",
    }


def validate_output_layout(source_paths: Sequence[str | Path], out_root: str | Path) -> None:
    """Reject layouts where the output directory would contain the source path.

    A nested output directory under a source root is allowed because it is excluded
    from source traversal. The opposite layout is unsafe: writing generated files
    into the same directory as the source root, or above it, can mix source and
    generated artifacts.
    """
    resolved_out = resolve_path(Path(out_root))
    for source_path in source_paths:
        resolved_source = resolve_path(Path(source_path))
        if resolved_out == resolved_source or resolved_out in resolved_source.parents:
            raise ValueError("output directory cannot be equal to or contain a source path")


def load_sources(source_paths: Sequence[str | Path], exclude_roots: Sequence[str | Path] = ()) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    resolved_excludes = [resolve_path(Path(path)) for path in exclude_roots]
    for path_arg in source_paths:
        path = Path(path_arg)
        if not path.exists():
            raise FileNotFoundError(f"source path does not exist: {path}")
        files = sorted(iter_text_files(path, resolved_excludes), key=lambda item: item.as_posix())
        for file_path in files:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            digest = sha256_text(text)
            sources.append(
                {
                    "source_id": f"source-{digest[:12]}",
                    "path": file_path,
                    "display_path": safe_display_path(file_path, path),
                    "text": text,
                    "sha256": digest,
                }
            )
    return sources


def iter_text_files(path: Path, exclude_roots: Sequence[Path] = ()) -> Iterable[Path]:
    if path_is_under(path, exclude_roots):
        return
    if path.is_file():
        if is_text_source(path):
            yield path
        return
    for child in path.rglob("*"):
        if path_is_under(child, exclude_roots):
            continue
        if child.is_file() and is_text_source(child):
            yield child


def resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def path_is_under(path: Path, roots: Sequence[Path]) -> bool:
    resolved = resolve_path(path)
    for root in roots:
        if resolved == root or root in resolved.parents:
            return True
    return False


def is_text_source(path: Path) -> bool:
    return path.suffix.casefold() in TEXT_SUFFIXES


def safe_display_path(file_path: Path, root_arg: Path) -> str:
    """Return a useful non-absolute source path for public artifacts."""
    try:
        if root_arg.is_dir():
            return file_path.relative_to(root_arg).as_posix()
    except ValueError:
        pass
    return file_path.name


def classify_text(text: str) -> List[Dict[str, Any]]:
    normalized = text.casefold()
    matches: List[Dict[str, Any]] = []
    for definition in DOMAIN_DEFINITIONS:
        matched_keywords = non_overlapping_keyword_matches(normalized, definition.keywords)
        if len(matched_keywords) < definition.min_score:
            continue
        matches.append(
            {
                "id": definition.id,
                "score": len(matched_keywords),
                "matched_keywords": matched_keywords,
            }
        )
    return matches


def non_overlapping_keyword_matches(normalized_text: str, keywords: Sequence[str]) -> List[str]:
    """Return unique keyword matches, counting overlapping phrases as one signal.

    Longer phrases win over substrings (for example `paid willingness` beats
    the embedded `willingness`, while a later standalone `willingness` still
    counts as a second signal). ASCII keywords also need simple alphanumeric
    boundaries so substrings inside longer words do not count.
    """
    candidates: List[tuple[int, int, str]] = []
    for keyword in keywords:
        normalized_keyword = keyword.casefold()
        for start, end in find_keyword_spans(normalized_text, normalized_keyword):
            candidates.append((start, end, keyword))

    selected: List[tuple[int, int, str]] = []
    for start, end, keyword in sorted(candidates, key=lambda item: (-(item[1] - item[0]), item[0], item[2])):
        if any(spans_overlap(start, end, selected_start, selected_end) for selected_start, selected_end, _ in selected):
            continue
        selected.append((start, end, keyword))
    return sorted({keyword for _, _, keyword in selected})


def find_keyword_spans(normalized_text: str, normalized_keyword: str) -> List[tuple[int, int]]:
    spans: List[tuple[int, int]] = []
    start = 0
    while True:
        index = normalized_text.find(normalized_keyword, start)
        if index == -1:
            return spans
        end = index + len(normalized_keyword)
        if has_keyword_boundaries(normalized_text, index, end, normalized_keyword):
            spans.append((index, end))
        start = index + 1


def has_keyword_boundaries(text: str, start: int, end: int, keyword: str) -> bool:
    if not keyword or not keyword.isascii():
        return True
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    return not is_ascii_word_char(before) and not is_ascii_word_char(after)


def is_ascii_word_char(char: str) -> bool:
    return bool(char) and (char.isascii() and (char.isalnum() or char == "_"))


def spans_overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end


def domain_record(definition: DomainDefinition, hit: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "record_type": "domain",
        "id": definition.id,
        "title": definition.title,
        "summary": definition.summary,
        "status": "active",
        "source_count": int(hit["source_count"]),
        "score": int(hit["score"]),
        "matched_keywords": list(hit["matched_keywords"]),
    }


def write_domain_artifacts(
    out_root: Path,
    registry: Mapping[str, Any],
    assignments: Sequence[Mapping[str, Any]],
    unassigned: Sequence[Mapping[str, Any]],
) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    reset_generated_domains_dir(out_root)
    (out_root / GENERATED_MARKER).write_text("generated by mindpack_kit discover-domains\n", encoding="utf-8")
    (out_root / "registry.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_jsonl(out_root / "domain_manifest.jsonl", registry["domains"])
    write_jsonl(out_root / "source_assignments.jsonl", assignments)
    write_jsonl(out_root / "unassigned_sources.jsonl", unassigned)
    (out_root / "domain_coverage_report.md").write_text(render_coverage_report(registry, assignments, unassigned), encoding="utf-8")

    domains_root = out_root / "domains"
    domains_root.mkdir(parents=True, exist_ok=True)
    for domain in registry["domains"]:
        domain_dir = domains_root / str(domain["id"])
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / "README.md").write_text(render_domain_readme(domain), encoding="utf-8")


def write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def reset_generated_domains_dir(out_root: Path) -> None:
    domains_root = out_root / "domains"
    if not domains_root.exists():
        return
    if domains_root.is_symlink() or not domains_root.is_dir():
        raise ValueError(f"refusing to replace unsafe generated domains path: {domains_root}")
    if not output_dir_has_generated_marker(out_root):
        raise ValueError(
            "refusing to remove existing domains directory without a Mindpack domain-registry marker"
        )
    shutil.rmtree(domains_root)


def output_dir_has_generated_marker(out_root: Path) -> bool:
    if (out_root / GENERATED_MARKER).is_file():
        return True
    registry_path = out_root / "registry.json"
    if not registry_path.is_file():
        return False
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(registry, dict) and registry.get("format") == "mindpack.domain-registry.v0"


def render_coverage_report(registry: Mapping[str, Any], assignments: Sequence[Mapping[str, Any]], unassigned: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Domain Coverage Report",
        "",
        "아이디어 도메인 하나로 압축하지 않음: mixed sources are split into explicit Mindpack domains.",
        "",
        f"- Sources: {registry['source_count']}",
        f"- Active domains: {len(registry['domains'])}",
        f"- Assigned sources: {len(assignments)}",
        f"- Unassigned sources: {len(unassigned)}",
        "",
        "## Active Domains",
    ]
    if registry["domains"]:
        for domain in registry["domains"]:
            keywords = ", ".join(domain.get("matched_keywords", [])[:8])
            lines.append(f"- `{domain['id']}` — {domain['summary']} (score: {domain['score']}; keywords: {keywords})")
    else:
        lines.append("- None")

    lines.extend(["", "## Unassigned Sources"])
    if unassigned:
        for source in unassigned:
            lines.append(f"- `{source['source_id']}` — {source['path']}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def render_domain_readme(domain: Mapping[str, Any]) -> str:
    keywords = "\n".join(f"- {keyword}" for keyword in domain.get("matched_keywords", [])) or "- None recorded"
    return f"""# {domain['title']}

Domain ID: `{domain['id']}`

Status: `{domain['status']}`

{domain['summary']}

## Discovery Evidence

- Source count: {domain['source_count']}
- Score: {domain['score']}

## Matched Keywords

{keywords}
"""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
