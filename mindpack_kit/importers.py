"""Conversation export/import helpers for Mindpack.

This module normalizes local AI-agent chat exports into a small common
Conversation JSONL shape. It intentionally keeps the parser conservative: only
message text becomes normalized turns, and provider/tool metadata is dropped.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .ontology import (
    approve_candidates,
    compile_ontology_pack,
    ingest_conversation,
    init_ontology_workspace,
    read_jsonl_if_exists,
    sha256_file,
    sha256_text,
    slugify,
    write_jsonl,
)

CHAT_SOURCE_CHOICES = ("auto", "generic", "codex", "claude-code")
MESSAGE_ROLES = {"user", "assistant", "system", "developer", "unknown"}
ROLE_ALIASES = {
    "human": "user",
    "ai": "assistant",
    "agent": "assistant",
    "bot": "assistant",
}
TEXT_BLOCK_TYPES = {"", "text", "input_text", "output_text", "message"}
SKIP_BLOCK_TYPES = {
    "tool_use",
    "tool_result",
    "tool_call",
    "function_call",
    "function_result",
    "command",
    "summary",
    "reasoning",
    "thinking",
}
SKIP_RECORD_TYPES = {
    "session",
    "summary",
    "metadata",
    "config",
    "configuration",
    "environment",
    "env",
    "workspace",
    "cwd",
    "tool_use",
    "tool_result",
    "tool_call",
    "function_call",
    "function_result",
    "command",
}
SKIP_RAW_ROLES = {
    "tool",
    "tool_use",
    "tool_result",
    "tool_call",
    "function",
    "function_call",
    "function_result",
    "command",
}
MESSAGE_RECORD_TYPES = {"", "message", "conversation_turn", "user", "assistant", "system", "developer"}


def import_chat_export(
    source_file: str | Path,
    out_file: str | Path | None = None,
    *,
    ontology_dir: str | Path | None = None,
    source: str = "auto",
    source_id: str | None = None,
    conversation_id: str | None = None,
    title: str | None = None,
    url: str | None = None,
) -> Dict[str, Any]:
    """Normalize a local chat export and optionally ingest it into an ontology."""
    if source not in CHAT_SOURCE_CHOICES:
        raise ValueError(f"unsupported source: {source}")
    if out_file is None and ontology_dir is None:
        raise ValueError("import-chat requires --out or --ontology")

    source_path = Path(source_file)
    if not source_path.is_file():
        raise FileNotFoundError(f"chat export source does not exist: {source_path}")

    safe_source_id = slugify(source_id) if source_id else "source-" + sha256_file(source_path)[:12]
    if out_file is None:
        root = Path(ontology_dir)  # type: ignore[arg-type]
        out_path = root / "raw" / "conversations" / f"{safe_source_id}.import.jsonl"
    else:
        out_path = Path(out_file)

    resolved_source = detect_source(source_path, source)
    turns = load_chat_turns(source_path, resolved_source)
    records = conversation_records(
        turns,
        source=resolved_source,
        source_id=safe_source_id,
        conversation_id=conversation_id or safe_source_id,
        title=title,
        url=url,
    )
    write_jsonl(out_path, records)

    report: Dict[str, Any] = {
        "source": resolved_source,
        "source_id": safe_source_id,
        "conversation_id": conversation_id or safe_source_id,
        "turn_count": len(records),
        "out_path": str(out_path),
    }

    if ontology_dir is not None:
        ingest_report = ingest_conversation(out_path, ontology_dir, safe_source_id)
        report.update(
            {
                "ontology_dir": str(ontology_dir),
                "candidate_count": ingest_report["candidate_count"],
                "candidate_ids": ingest_report.get("candidate_ids", []),
                "pending_path": ingest_report["pending_path"],
                "raw_path": ingest_report["raw_path"],
            }
        )
    return report


def run_ontology_workflow(
    source_file: str | Path,
    work_dir: str | Path,
    *,
    pack_id: str,
    title: str,
    question: str,
    source: str = "auto",
    source_id: str | None = None,
    approve_all_tagged: bool = False,
) -> Dict[str, Any]:
    """Run the local conversation-to-ontology workflow in one command."""
    from .compiler import validate_pack, write_runtime_context

    work_root = Path(work_dir)
    ontology_root = work_root / "ontology"
    pack_root = work_root / "pack"
    init_ontology_workspace(ontology_root, pack_id, title)
    import_report = import_chat_export(
        source_file,
        ontology_dir=ontology_root,
        source=source,
        source_id=source_id,
        title=title,
    )

    report: Dict[str, Any] = {
        "status": "pending_review",
        "work_dir": str(work_root),
        "ontology_dir": str(ontology_root),
        "pack_dir": str(pack_root),
        **import_report,
    }
    if not approve_all_tagged:
        return report

    current_ids = [str(candidate_id) for candidate_id in import_report.get("candidate_ids", []) if candidate_id]
    if not current_ids:
        raise ValueError("no pending candidates found for the current import; nothing to approve")
    approval_report = approve_candidates(
        ontology_root,
        current_ids,
        source_ref_filter=(str(import_report["source_id"]), str(import_report["raw_path"])),
    )
    compile_report = compile_ontology_pack(ontology_root, pack_root, pack_id, title)
    valid, messages = validate_pack(pack_root)
    if not valid:
        raise ValueError("compiled ontology pack is invalid: " + "; ".join(messages))
    context_path = pack_root / "samples" / "runtime_context.md"
    write_runtime_context(pack_root, question, context_path)

    report.update(
        {
            "status": "compiled",
            "approved_count": approval_report["approved_count"],
            "ontology_entry_count": compile_report["ontology_entry_count"],
            "graph_node_count": compile_report["graph_node_count"],
            "valid": True,
            "runtime_context_path": str(context_path),
        }
    )
    return report


def current_import_candidate_ids(candidates: Sequence[Mapping[str, Any]], source_id: str, raw_path: str) -> List[str]:
    """Return pending candidate IDs that came from the current import only."""
    ids: List[str] = []
    for candidate in candidates:
        refs = candidate.get("source_refs") or []
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, Mapping):
                continue
            if str(ref.get("source_id") or "") == source_id and str(ref.get("source_path") or "") == raw_path:
                candidate_id = str(candidate.get("id") or "")
                if candidate_id:
                    ids.append(candidate_id)
                break
    return ids


def conversation_records(
    turns: Sequence[Mapping[str, Any]],
    *,
    source: str,
    source_id: str,
    conversation_id: str,
    title: str | None,
    url: str | None,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for turn in turns:
        text = str(turn.get("text") or "").strip()
        if not text:
            continue
        record: Dict[str, Any] = {
            "record_type": "conversation_turn",
            "source": source,
            "source_id": source_id,
            "conversation_id": conversation_id,
            "turn": len(records) + 1,
            "role": normalize_role(str(turn.get("role") or "unknown")),
            "text": text,
            "sha256": sha256_text(text),
        }
        if title:
            record["title"] = title
        if url:
            record["url"] = url
        records.append(record)
    return records


def detect_source(source_path: Path, source: str) -> str:
    if source != "auto":
        return source
    try:
        sample = source_path.read_text(encoding="utf-8", errors="ignore")[:4096]
    except OSError:
        return "generic"
    if "claude-code.synthetic.jsonl.v0" in sample:
        return "claude-code"
    if "codex.synthetic.jsonl.v0" in sample:
        return "codex"
    return "generic"


def load_chat_turns(source_path: Path, source: str) -> List[Dict[str, Any]]:
    if source == "codex":
        return load_codex_turns(source_path)
    if source == "claude-code":
        return load_claude_code_turns(source_path)
    return load_generic_turns(source_path)


def load_generic_turns(source_path: Path) -> List[Dict[str, Any]]:
    if source_path.suffix.lower() == ".json":
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        return [turn for record in iter_message_records(payload) if (turn := turn_from_record(record))]
    if source_path.suffix.lower() == ".jsonl":
        turns: List[Dict[str, Any]] = []
        for record in load_jsonl_records(source_path):
            turn = turn_from_record(record)
            if turn:
                turns.append(turn)
        return turns
    return load_text_turns(source_path)


def load_codex_turns(source_path: Path) -> List[Dict[str, Any]]:
    turns: List[Dict[str, Any]] = []
    for record in iter_message_records(load_records_payload(source_path)):
        for message in iter_codex_message_records(record):
            turn = turn_from_record(message, strict_message=True, provider="codex")
            if turn:
                turns.append(turn)
    return turns


def load_claude_code_turns(source_path: Path) -> List[Dict[str, Any]]:
    turns: List[Dict[str, Any]] = []
    for record in iter_message_records(load_records_payload(source_path)):
        record_type = str(record.get("type") or "").lower()
        if record_type in SKIP_RECORD_TYPES:
            continue
        message = record.get("message") if isinstance(record.get("message"), Mapping) else record
        if not isinstance(message, Mapping):
            continue
        role = normalize_role(str(message.get("role") or record.get("type") or "unknown"))
        if role not in MESSAGE_ROLES - {"unknown"}:
            continue
        text = flatten_content(message.get("content"), provider="claude-code")
        if text:
            turns.append({"role": role, "text": text})
    return turns


def load_records_payload(source_path: Path) -> Any:
    if source_path.suffix.lower() == ".jsonl":
        return load_jsonl_records(source_path)
    if source_path.suffix.lower() == ".json":
        return json.loads(source_path.read_text(encoding="utf-8"))
    return [{"role": turn["role"], "text": turn["text"]} for turn in load_text_turns(source_path)]


def load_jsonl_records(source_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {source_path}:{line_number}: {exc}") from exc
        if isinstance(payload, dict):
            records.append(payload)
    return records


def load_text_turns(source_path: Path) -> List[Dict[str, Any]]:
    turns: List[Dict[str, Any]] = []
    text = source_path.read_text(encoding="utf-8")
    in_frontmatter = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if stripped.startswith("<!--") or stripped.endswith("-->"):
            continue
        role = "unknown"
        turn_text = stripped
        if ":" in stripped:
            prefix, remainder = stripped.split(":", 1)
            normalized_prefix = normalize_role(prefix.strip())
            if normalized_prefix in MESSAGE_ROLES - {"unknown"}:
                role = normalized_prefix
                turn_text = remainder.strip()
        if turn_text:
            turns.append({"role": role, "text": turn_text})
    return turns


def iter_message_records(payload: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from iter_message_records(item)
        return
    if not isinstance(payload, Mapping):
        return

    record_type = str(payload.get("type") or payload.get("event") or "").lower()
    if record_type in SKIP_RECORD_TYPES:
        return

    for key in ("messages", "conversation", "turns", "items", "data", "output"):
        value = payload.get(key)
        if isinstance(value, (list, Mapping)):
            yield from iter_message_records(value)

    mapping = payload.get("mapping")
    if isinstance(mapping, Mapping):
        for item in mapping.values():
            yield from iter_message_records(item)

    response = payload.get("response")
    if isinstance(response, Mapping):
        yield from iter_message_records(response)

    message = payload.get("message")
    if isinstance(message, Mapping):
        merged = dict(message)
        if "type" not in merged and payload.get("type"):
            merged["type"] = payload.get("type")
        yield merged
        if not any(key in payload for key in ("role", "content", "text")):
            return

    if any(key in payload for key in ("role", "content", "text", "message", "event", "type")):
        yield payload


def iter_codex_message_records(record: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    record_type = str(record.get("type") or record.get("event") or "").lower()
    if record_type in SKIP_RECORD_TYPES:
        return
    if record.get("response") or record.get("output"):
        yield from iter_message_records({"response": record.get("response"), "output": record.get("output")})
    role = normalize_role(str(record.get("role") or "unknown"))
    if role in MESSAGE_ROLES - {"unknown"} and any(key in record for key in ("content", "text", "message")):
        yield record


def turn_from_record(record: Mapping[str, Any], *, strict_message: bool = False, provider: str = "generic") -> Dict[str, Any] | None:
    record_type = str(record.get("type") or record.get("event") or "").lower()
    if record_type in SKIP_RECORD_TYPES:
        return None
    if record_type not in MESSAGE_RECORD_TYPES and "role" not in record:
        return None
    raw_role = str(record.get("role") or record.get("type") or "unknown")
    if raw_role.strip().lower() in SKIP_RAW_ROLES:
        return None
    role = normalize_role(raw_role)
    if strict_message and role not in MESSAGE_ROLES - {"unknown"}:
        return None
    text = ""
    if "text" in record:
        text = flatten_content(record.get("text"), provider=provider)
    elif "content" in record:
        text = flatten_content(record.get("content"), provider=provider)
    elif "message" in record:
        message = record.get("message")
        if isinstance(message, Mapping):
            role = normalize_role(str(message.get("role") or role))
            text = flatten_content(message.get("content") or message.get("text"), provider=provider)
        else:
            text = flatten_content(message, provider=provider)
    if not text:
        return None
    return {"role": role, "text": text}


def flatten_content(value: Any, *, provider: str = "generic") -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [flatten_content(item, provider=provider) for item in value]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, Mapping):
        block_type = str(value.get("type") or value.get("event") or "").lower()
        if block_type in SKIP_BLOCK_TYPES:
            return ""
        if block_type not in TEXT_BLOCK_TYPES and provider in {"codex", "claude-code"}:
            return ""
        if "text" in value:
            return flatten_content(value.get("text"), provider=provider)
        if "content" in value:
            return flatten_content(value.get("content"), provider=provider)
        if "message" in value:
            return flatten_content(value.get("message"), provider=provider)
    return ""


def normalize_role(role: str) -> str:
    normalized = ROLE_ALIASES.get(role.strip().lower(), role.strip().lower())
    return normalized if normalized in MESSAGE_ROLES else "unknown"
