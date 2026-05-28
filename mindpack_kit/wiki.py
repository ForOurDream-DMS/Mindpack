"""Wiki initialization helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .templates import get_wiki_files


def init_wiki(out_dir: str | Path, profile: str) -> list[Path]:
    """Create a source LLM Wiki directory for *profile*.

    Existing files are overwritten to keep the command deterministic for local use.
    Returns the paths written.
    """
    root = Path(out_dir)
    files = get_wiki_files(profile)
    written: list[Path] = []
    for relative_path, content in sorted(files.items()):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def expected_wiki_paths(profile: str) -> Iterable[str]:
    """Return the relative paths that init_wiki writes for a profile."""
    return sorted(get_wiki_files(profile))
