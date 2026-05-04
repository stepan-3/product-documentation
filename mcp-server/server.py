"""MCP server for the Wallarm product documentation repo.

Exposes tools that let agents (and people via MCP-aware clients) discover,
search, and read the markdown sources under ``docs/``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

REPO_ROOT = Path(
    os.environ.get("WALLARM_DOCS_ROOT", Path(__file__).resolve().parent.parent)
).resolve()
DOCS_ROOT = REPO_ROOT / "docs"
PUBLIC_BASE_URL = "https://docs.wallarm.com"

mcp = FastMCP("wallarm-docs")


def _safe_join(version: str, subpath: str = "") -> Path:
    """Resolve ``docs/<version>/<subpath>`` and refuse paths that escape it."""
    if not version or "/" in version or version.startswith("."):
        raise ValueError(f"Invalid version: {version!r}")
    base = (DOCS_ROOT / version).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Unknown docs version: {version!r}")
    target = (base / subpath).resolve() if subpath else base
    if base != target and base not in target.parents:
        raise ValueError(f"Path escapes docs/{version}: {subpath!r}")
    return target


def _rel(path: Path) -> str:
    return str(path.relative_to(DOCS_ROOT))


@dataclass
class Hit:
    path: str
    score: int
    snippet: str


def _score(text_lower: str, terms: list[str]) -> int:
    score = 0
    for term in terms:
        score += text_lower.count(term)
    return score


def _make_snippet(text: str, terms: list[str], width: int = 240) -> str:
    text_lower = text.lower()
    pos = -1
    for term in terms:
        idx = text_lower.find(term)
        if idx != -1 and (pos == -1 or idx < pos):
            pos = idx
    if pos == -1:
        return text[:width].strip().replace("\n", " ")
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


@mcp.tool()
def list_versions() -> list[str]:
    """List the available documentation versions/locales (subdirs of ``docs/``)."""
    return sorted(p.name for p in DOCS_ROOT.iterdir() if p.is_dir())


@mcp.tool()
def list_docs(version: str = "latest", subdir: str = "", max_results: int = 500) -> list[str]:
    """List markdown files under ``docs/<version>/<subdir>``.

    Returns repo-relative paths (e.g. ``latest/api-discovery/overview.md``)
    suitable for passing to ``read_doc``.
    """
    base = _safe_join(version, subdir)
    if base.is_file():
        return [_rel(base)]
    paths: list[str] = []
    for p in sorted(base.rglob("*.md")):
        paths.append(_rel(p))
        if len(paths) >= max_results:
            break
    return paths


@mcp.tool()
def read_doc(path: str) -> str:
    """Read the full markdown content of a doc.

    ``path`` is a repo-relative path under ``docs/`` such as
    ``latest/sla.md`` or an absolute path inside the docs tree.
    """
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = DOCS_ROOT / path
    candidate = candidate.resolve()
    if DOCS_ROOT != candidate and DOCS_ROOT not in candidate.parents:
        raise ValueError(f"Path is outside docs/: {path!r}")
    if not candidate.is_file():
        raise FileNotFoundError(f"Doc not found: {path!r}")
    return candidate.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def search_docs(
    query: str,
    version: str = "latest",
    limit: int = 20,
    subdir: str = "",
) -> list[dict]:
    """Full-text search across markdown docs for the given version.

    Splits the query on whitespace, ranks files by how often the terms
    appear, and returns the best matches with a short snippet. Use
    ``read_doc`` on a returned ``path`` to fetch full content.
    """
    terms = [t.lower() for t in re.split(r"\s+", query.strip()) if t]
    if not terms:
        return []
    base = _safe_join(version, subdir)
    hits: list[Hit] = []
    for md in base.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lower = text.lower()
        if not all(term in lower for term in terms):
            # Require every term to appear; keeps results focused.
            continue
        score = _score(lower, terms)
        # Boost hits in headings and titles.
        for line in text.splitlines():
            if line.startswith("#") and all(t in line.lower() for t in terms):
                score += 5
                break
        hits.append(Hit(path=_rel(md), score=score, snippet=_make_snippet(text, terms)))
    hits.sort(key=lambda h: (-h.score, h.path))
    return [{"path": h.path, "score": h.score, "snippet": h.snippet} for h in hits[:limit]]


@mcp.tool()
def get_doc_url(path: str) -> str:
    """Return the public ``docs.wallarm.com`` URL for a repo-relative doc path.

    Only ``latest/`` paths map cleanly to the published site root; other
    versions are returned as best-effort prefixed URLs.
    """
    rel = path.lstrip("/")
    if rel.startswith("docs/"):
        rel = rel[len("docs/"):]
    parts = rel.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Expected '<version>/<path>.md', got: {path!r}")
    version, tail = parts
    tail = re.sub(r"\.md$", "/", tail)
    tail = re.sub(r"/index/$", "/", tail)
    if version == "latest":
        return f"{PUBLIC_BASE_URL}/{tail}"
    return f"{PUBLIC_BASE_URL}/{version}/{tail}"


def main() -> None:
    if not DOCS_ROOT.is_dir():
        raise SystemExit(f"docs/ not found at {DOCS_ROOT}. Set WALLARM_DOCS_ROOT.")
    mcp.run()


if __name__ == "__main__":
    main()
