"""Filesystem CRM: contact profiles as Markdown under data/profiles/."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config import PROFILES_DIR

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SECTION_ORDER = ("Summary", "Relationship", "Facts/Memories", "Notes")


@dataclass
class ProfileDoc:
    chat_id: int
    name: str = ""
    relationship: str = ""
    updated_at: str = ""
    summary: str = ""
    facts: str = ""
    notes: str = ""
    path: Path | None = None
    extra_frontmatter: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "name": self.name,
            "relationship": self.relationship,
            "updated_at": self.updated_at,
            "summary": self.summary,
            "facts": self.facts,
            "notes": self.notes,
            "filename": self.path.name if self.path else None,
            "path": str(self.path) if self.path else None,
            "markdown": render_markdown(self),
        }


def ensure_profiles_dir() -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


def slugify(name: str, fallback: str = "contact") -> str:
    raw = (name or "").strip().lower()
    slug = _SLUG_RE.sub("-", raw).strip("-")
    return slug or fallback


def profile_filename(chat_id: int, name: str = "") -> str:
    return f"{chat_id}-{slugify(name)}.md"


def _parse_frontmatter(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            continue
        meta[key] = value.strip().strip('"').strip("'")
    return meta


def _parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {name: "" for name in _SECTION_ORDER}
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current
        if current is not None:
            sections[current] = "\n".join(buf).strip()
        buf = []

    for line in body.splitlines():
        heading = line.strip()
        if heading.startswith("## "):
            title = heading[3:].strip()
            flush()
            current = title if title in sections else title
            if current not in sections:
                sections[current] = ""
            continue
        buf.append(line)
    flush()
    return sections


def parse_markdown(text: str, *, path: Path | None = None) -> ProfileDoc:
    text = text or ""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        # Tolerate bare body without frontmatter
        sections = _parse_sections(text)
        chat_id = 0
        if path and path.name:
            prefix = path.name.split("-", 1)[0]
            if prefix.lstrip("-").isdigit():
                chat_id = int(prefix)
        return ProfileDoc(
            chat_id=chat_id,
            summary=sections.get("Summary", ""),
            relationship=sections.get("Relationship", ""),
            facts=sections.get("Facts/Memories", ""),
            notes=sections.get("Notes", ""),
            path=path,
        )

    meta = _parse_frontmatter(match.group(1))
    sections = _parse_sections(match.group(2) or "")
    known = {"chat_id", "name", "updated_at", "relationship"}
    extra = {k: v for k, v in meta.items() if k not in known}
    try:
        chat_id = int(str(meta.get("chat_id", "0")).strip() or "0")
    except ValueError:
        chat_id = 0
    return ProfileDoc(
        chat_id=chat_id,
        name=meta.get("name", ""),
        relationship=meta.get("relationship", "") or sections.get("Relationship", ""),
        updated_at=meta.get("updated_at", ""),
        summary=sections.get("Summary", ""),
        facts=sections.get("Facts/Memories", ""),
        notes=sections.get("Notes", ""),
        path=path,
        extra_frontmatter=extra,
    )


def render_markdown(doc: ProfileDoc) -> str:
    relationship = (doc.relationship or "").strip()
    lines = [
        "---",
        f"chat_id: {doc.chat_id}",
        f'name: "{doc.name or ""}"',
        f"updated_at: {doc.updated_at or datetime.utcnow().isoformat()}",
        f'relationship: "{relationship.replace(chr(34), chr(39))}"',
    ]
    for key, value in sorted(doc.extra_frontmatter.items()):
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append((doc.summary or "").strip() or "_No summary yet._")
    lines.append("")
    lines.append("## Relationship")
    lines.append(relationship or "_No relationship notes yet._")
    lines.append("")
    lines.append("## Facts/Memories")
    lines.append((doc.facts or "").strip() or "_No facts yet._")
    lines.append("")
    lines.append("## Notes")
    lines.append((doc.notes or "").strip() or "_No notes yet._")
    lines.append("")
    return "\n".join(lines)


def _find_path_for_chat(chat_id: int) -> Path | None:
    ensure_profiles_dir()
    matches = sorted(PROFILES_DIR.glob(f"{chat_id}-*.md"))
    if matches:
        return matches[0]
    legacy = PROFILES_DIR / f"{chat_id}.md"
    return legacy if legacy.exists() else None


def list_profiles() -> list[dict[str, Any]]:
    ensure_profiles_dir()
    items: list[dict[str, Any]] = []
    for path in sorted(PROFILES_DIR.glob("*.md")):
        try:
            doc = read_profile_file(path)
        except Exception:
            continue
        items.append(
            {
                "chat_id": doc.chat_id,
                "name": doc.name,
                "relationship": doc.relationship,
                "updated_at": doc.updated_at,
                "filename": path.name,
            }
        )
    return items


def read_profile_file(path: Path) -> ProfileDoc:
    text = path.read_text(encoding="utf-8")
    return parse_markdown(text, path=path)


def get_profile(chat_id: int) -> ProfileDoc | None:
    path = _find_path_for_chat(chat_id)
    if not path:
        return None
    return read_profile_file(path)


def write_profile(doc: ProfileDoc, *, rename_if_needed: bool = True) -> ProfileDoc:
    ensure_profiles_dir()
    doc.updated_at = doc.updated_at or datetime.utcnow().isoformat()
    existing = _find_path_for_chat(doc.chat_id)
    target_name = profile_filename(doc.chat_id, doc.name)
    target = PROFILES_DIR / target_name

    if existing and existing != target and rename_if_needed:
        # Prefer canonical {chat_id}-{slug}.md; remove old path after write
        pass
    elif existing and not rename_if_needed:
        target = existing

    target.write_text(render_markdown(doc), encoding="utf-8")
    if existing and existing != target and existing.exists():
        existing.unlink()
    doc.path = target
    return doc


def save_profile_markdown(chat_id: int, markdown: str) -> ProfileDoc:
    doc = parse_markdown(markdown)
    doc.chat_id = chat_id
    if not doc.updated_at:
        doc.updated_at = datetime.utcnow().isoformat()
    return write_profile(doc)


def upsert_from_learn(
    chat_id: int,
    *,
    name: str = "",
    relationship: str = "",
    ai_context: str = "",
    facts: list[str] | None = None,
    notes: str | None = None,
) -> ProfileDoc:
    existing = get_profile(chat_id)
    fact_lines = []
    if facts:
        fact_lines = [f"- {f.strip()}" for f in facts if str(f).strip()]
    elif ai_context.strip():
        # Preserve bullet-ish context as facts when no structured facts
        fact_lines = [
            line if line.startswith("-") else f"- {line}"
            for line in ai_context.strip().splitlines()
            if line.strip()
        ]

    doc = ProfileDoc(
        chat_id=chat_id,
        name=(name or (existing.name if existing else "") or f"Chat {chat_id}"),
        relationship=relationship or (existing.relationship if existing else ""),
        updated_at=datetime.utcnow().isoformat(),
        summary=(
            (ai_context.strip().splitlines()[0].lstrip("- ").strip() if ai_context.strip() else "")
            or (existing.summary if existing else "")
        ),
        facts="\n".join(fact_lines) if fact_lines else (existing.facts if existing else ""),
        notes=notes if notes is not None else (existing.notes if existing else ""),
        extra_frontmatter=existing.extra_frontmatter if existing else {},
    )
    return write_profile(doc)
