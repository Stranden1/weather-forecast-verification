"""Bounded, read-only documentation access. No database or collector imports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1_000_000
# Discover Markdown at the root and under these existing documentation locations.
# Never traverse data, hidden directories, environments, or arbitrary browser paths.
DOC_FOLDERS = ("work", "outputs", "docs", "research", "cloud", "site")
PRIMARY = {
    "Project Status": "PROJECT_STATUS.md",
    "Next Steps": "NEXT_STEPS.md",
    "Decisions": "DECISIONS.md",
    "Work Status": "WORK_STATUS.md",
}


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    modified: datetime


def contained_file(root: Path, candidate: Path) -> Path:
    """Reject symlinks/junctions at every level, even ones pointing inside root."""
    root = root.resolve(strict=True)
    candidate = candidate.absolute()
    relative = candidate.relative_to(root)
    node = root
    for part in relative.parts:
        if part in {".", ".."}:
            raise ValueError("Invalid path")
        node = node / part
        if node.is_symlink() or node.is_junction():
            raise ValueError("Linked paths are not documentation sources")
    resolved = node.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("Source is not a file inside the project")
    return resolved


def discover(root: Path = ROOT) -> dict[str, Path]:
    root = root.resolve(strict=True)
    candidates = [p for p in root.glob("*.md") if not p.name.startswith(".")]
    for name in DOC_FOLDERS:
        base = root / name
        if not base.is_dir() or base.is_symlink() or base.is_junction():
            continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            here = Path(directory)
            dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                             and d not in {"node_modules", "__pycache__"}
                             and not (here / d).is_symlink()
                             and not (here / d).is_junction())
            candidates.extend(here / f for f in files if f.lower().endswith(".md")
                              and not f.startswith("."))
    found = {}
    for candidate in sorted(candidates):
        try:
            path = contained_file(root, candidate)
            if path.stat().st_size <= MAX_BYTES:
                found[candidate.relative_to(root).as_posix()] = path
        except (OSError, ValueError):
            continue
    return found


def read_document(doc_id: str, catalog: dict[str, Path], root: Path = ROOT) -> Document:
    # The browser selects an ID; it never supplies an unrestricted filesystem path.
    if doc_id not in catalog:
        raise ValueError("Document is not in the discovered catalog")
    path = contained_file(root, catalog[doc_id])
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        content = handle.read(MAX_BYTES + 1)
        after = os.fstat(handle.fileno())
    if len(content) > MAX_BYTES:
        raise ValueError("Document exceeds the 1 MB reading limit")
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise ValueError("Document changed while reading; refresh to reload")
    return Document(doc_id, content.decode("utf-8-sig"),
                    datetime.fromtimestamp(after.st_mtime, timezone.utc))


def sections(text: str) -> list[tuple[str, str]]:
    """Split H2 sections outside code fences; keep source wording verbatim."""
    result = []
    title, lines, fence = "Introduction", [], None
    for line in text.splitlines(keepends=True):
        mark = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if mark:
            token = mark[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        heading = re.match(r"^##\s+(.+?)\s*#*\s*$", line) if fence is None else None
        if heading:
            if lines:
                result.append((title, "".join(lines)))
            title, lines = heading[1], [line]
        else:
            lines.append(line)
    if lines:
        result.append((title, "".join(lines)))
    return result


def latest_section(text: str) -> tuple[str, str]:
    parts = sections(text)
    dated = [(max(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", title)), i, title, body)
             for i, (title, body) in enumerate(parts)
             if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", title)]
    if dated:
        _, _, title, body = max(dated)
        return title, body
    return parts[-1] if parts else ("Empty document", "")


def document_url(doc_id: str) -> str:
    return "?doc=" + quote(doc_id, safe="")


def display_markdown(text: str, doc_id: str, catalog: dict[str, Path]) -> str:
    """Route local Markdown links into HQ; don't embed remote/local images.

    Raw HTML is separately disabled by the renderer. Non-Markdown local file links
    stay as readable paths rather than exposing a generic file-serving endpoint.
    """
    def link_target(target: str) -> str | None:
        target = target.strip().strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme in {"https", "http", "mailto"}:
            return target
        if parsed.scheme or parsed.netloc:
            return None
        if target.startswith("#"):
            return target
        relative = (Path(doc_id).parent / unquote(parsed.path)).as_posix()
        relative = os.path.normpath(relative).replace("\\", "/")
        if relative in catalog:
            return document_url(relative) + ("#" + parsed.fragment if parsed.fragment else "")
        return None

    def inline(match):
        label, target = match[1], match[2]
        # Support optional Markdown titles without treating them as part of the path.
        target = re.split(r'\s+[\"\']', target, maxsplit=1)[0]
        routed = link_target(target)
        return f"[{label}]({routed})" if routed else f"{label} (`{target}`)"

    rendered, fence = [], None
    for line in text.splitlines(keepends=True):
        mark = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if mark:
            token = mark[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            rendered.append(line)
            continue
        if fence is None:
            line = line.replace("![", "[Image: ")
            definition = re.match(r"^\s{0,3}\[([^]]+)\]:\s*(\S+)(.*)$", line)
            if definition:
                target = link_target(definition[2])
                line = f"[{definition[1]}]: {target}\n" if target else f"{definition[1]}: `{definition[2]}`\n"
            else:
                line = re.sub(r"\[([^]\n]+)\]\(([^)\n]+)\)", inline, line)
        rendered.append(line)
    return "".join(rendered)


def context_text(documents: list[Document], recent_decisions: bool = True) -> str:
    parts = ["# WeatherApp — selected project context\n\n"
             "Verbatim source excerpts. Dates describe the source, not a fresh validation.\n"]
    for doc in documents:
        body = latest_section(doc.text)[1] if recent_decisions and doc.id == "DECISIONS.md" else doc.text
        scope = "latest dated section" if recent_decisions and doc.id == "DECISIONS.md" else "full document"
        parts.append(f"\n---\n\nSource: {doc.id} ({scope})\n"
                     f"File modified: {doc.modified.isoformat()}\n\n{body.rstrip()}\n")
    return "".join(parts)
