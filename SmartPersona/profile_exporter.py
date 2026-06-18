"""
Export SmartPersona memories into a structured Markdown profile.

Dual use:
  1. Agent context — frontmatter + concise bullets for OpenClaw / chatbots
  2. Profile card — fuller sections for personal growth and review
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

PROFILE_VERSION = 1
MEMORY_TYPES = (
    "fact",
    "event",
    "preference",
    "habit",
    "belief",
    "relationship",
    "voice",
    "topic_style",
    "reaction",
)


def _normalize_memory_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, (list, dict)):
        return "Conversation (consolidated)."
    return str(content).strip()
DEFAULT_PROFILE_FILENAME = "user_profile.md"

# Section display order and human labels
SECTION_LABELS = {
    "fact": "Facts & background",
    "relationship": "Relationships",
    "preference": "Preferences",
    "habit": "Habits",
    "belief": "Beliefs & values",
    "voice": "Voice & tone",
    "topic_style": "Topic communication",
    "reaction": "Reactions & triggers",
    "event": "Notable events",
}

GROWTH_PROMPTS = [
    "What patterns do I notice in how I communicate with the people listed above?",
    "Which preferences or habits serve me well, and which might I want to change?",
    "What beliefs show up repeatedly — are they still true for who I want to become?",
    "What would I want an assistant or coach to remember about me after reading this profile?",
]


def default_profile_path(data_dir: Optional[str] = None) -> str:
    """Return the default on-disk path for the user profile markdown."""
    base = data_dir or os.path.dirname(os.path.abspath(__file__))
    env_path = (os.getenv("SMARTPERSONA_PROFILE_PATH") or "").strip()
    if env_path:
        return os.path.abspath(env_path)
    return os.path.join(base, DEFAULT_PROFILE_FILENAME)


def _persona_dict(persona: Any = None) -> dict[str, str]:
    if persona is None:
        return {}
    if isinstance(persona, Mapping):
        return {k: str(v) for k, v in persona.items() if v is not None}
    fields = ("name", "age", "gender", "occupation", "location", "email", "phone", "address")
    out = {}
    for key in fields:
        val = getattr(persona, key, None)
        if val is not None and str(val).strip():
            out[key] = str(val)
    return out


def _format_ts(ts: Any) -> str:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def _group_memories(memories: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {t: [] for t in MEMORY_TYPES}
    for entry in memories:
        if not isinstance(entry, dict):
            continue
        content = _normalize_memory_content(entry.get("content"))
        if not content:
            continue
        typ = entry.get("type", "fact")
        if typ not in grouped:
            typ = "fact"
        grouped[typ].append({**entry, "content": content})
    return grouped


def _memory_line(entry: Mapping[str, Any]) -> str:
    content = entry.get("content", "")
    person = (entry.get("person") or "").strip()
    topic = (entry.get("topic") or "").strip()
    situation = (entry.get("situation") or "").strip()
    participants = (entry.get("participants") or "").strip()
    ts = _format_ts(entry.get("timestamp"))

    prefix = ""
    if person:
        prefix = f"**{person}** — "
    elif participants:
        prefix = f"*{participants}* — "
    elif topic:
        prefix = f"[{topic}] "
    elif situation:
        prefix = f"({situation}) "

    line = f"- {prefix}{content}"
    if ts:
        line += f" _(learned {ts})_"
    return line


def _agent_context_bullets(
    persona: dict[str, str],
    grouped: dict[str, list[dict[str, Any]]],
    people: Sequence[str],
    max_chars: int = 2800,
) -> list[str]:
    """Concise bullets optimized for LLM system/context injection."""
    bullets: list[str] = []
    name = persona.get("name", "User")
    identity_bits = [name]
    for key in ("age", "gender", "occupation", "location"):
        if persona.get(key):
            identity_bits.append(str(persona[key]))
    bullets.append(f"Identity: {', '.join(identity_bits)}.")

    def add_section(label: str, entries: list[dict[str, Any]], limit: int, fmt=None):
        nonlocal bullets
        for entry in entries[-limit:]:
            text = fmt(entry) if fmt else entry.get("content", "")
            text = _normalize_memory_content(text)
            if text:
                bullets.append(f"{label}: {text}")

    add_section(
        "Relationship",
        grouped.get("relationship", []),
        8,
        lambda e: (
            f"{e.get('person', '').strip()}: {e.get('content', '')}"
            if e.get("person")
            else e.get("content", "")
        ),
    )
    add_section("Prefers", grouped.get("preference", []), 10)
    add_section("Habit", grouped.get("habit", []), 6)
    add_section("Believes", grouped.get("belief", []), 6)
    add_section("Speaks like", grouped.get("voice", []), 4)
    add_section("Fact", grouped.get("fact", []), 12)
    if people:
        bullets.append(f"People in life: {', '.join(people[:12])}.")

    # Trim to budget while keeping identity line
    out = [bullets[0]] if bullets else []
    size = len(out[0]) if out else 0
    for b in bullets[1:]:
        if size + len(b) + 1 > max_chars:
            break
        out.append(b)
        size += len(b) + 1
    return out


def build_user_profile_markdown(
    memories: Sequence[Mapping[str, Any]],
    persona: Any = None,
    thoughts: Optional[Sequence[Mapping[str, Any]]] = None,
    people: Optional[Sequence[str]] = None,
) -> str:
    """
    Build the full profile markdown string from raw memory/thought records.

    Parameters
    ----------
    memories : list of memory dicts (type, content, timestamp, optional person/topic/...)
    persona : SmartPersona instance, dict, or None
    thoughts : optional list of {thought, context, timestamp}
    people : optional precomputed people list; inferred from memories if omitted
    """
    persona_info = _persona_dict(persona)
    grouped = _group_memories(memories)
    display_name = persona_info.get("name", "User")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if people is None:
        people = _distinct_people(memories)

    agent_bullets = _agent_context_bullets(persona_info, grouped, people)
    counts = {t: len(grouped.get(t, [])) for t in MEMORY_TYPES}
    total = sum(counts.values())

    lines: list[str] = [
        "---",
        f"title: {display_name} — SmartPersona Profile",
        f"generated_at: {generated_at}",
        f"smartpersona_version: {PROFILE_VERSION}",
        "usage:",
        "  - openclaw_context",
        "  - chatbot_system_prompt",
        "  - personal_growth",
        "---",
        "",
        f"# {display_name} — Persona Profile",
        "",
        "> Auto-generated by **SmartPersona** from learned memories.",
        "> Paste the **Agent context** section into chatbots, OpenClaw, or any assistant that should know you.",
        "",
        "## Agent context",
        "",
        "_Copy from here for LLM system prompts or OpenClaw skills._",
        "",
    ]
    lines.extend(agent_bullets or ["- No memories recorded yet. Teach SmartPersona from chats or add memories manually."])
    lines.extend(["", "---", "", "## Identity", ""])

    if persona_info:
        for key, label in (
            ("name", "Name"),
            ("age", "Age"),
            ("gender", "Gender"),
            ("occupation", "Occupation"),
            ("location", "Location"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("address", "Address"),
        ):
            if persona_info.get(key):
                lines.append(f"- **{label}:** {persona_info[key]}")
    else:
        lines.append("- _Set `PERSONA_*` in `.env` or pass a persona object for static identity fields._")

    section_order = (
        "relationship",
        "fact",
        "preference",
        "habit",
        "belief",
        "voice",
        "topic_style",
        "reaction",
        "event",
    )
    event_limit = 20
    for typ in section_order:
        entries = grouped.get(typ, [])
        if not entries:
            continue
        if typ == "event":
            entries = entries[-event_limit:]
        lines.extend(["", f"## {SECTION_LABELS[typ]}", ""])
        for entry in entries:
            lines.append(_memory_line(entry))

    lines.extend(["", "## Growth & reflection", ""])
    thought_list = list(thoughts or [])
    if thought_list:
        lines.append("_Recent persona thoughts — use these for journaling or coaching prompts._")
        lines.append("")
        for t in thought_list[-15:]:
            text = (t.get("thought") or "").strip()
            if not text:
                continue
            ctx = (t.get("context") or "").strip()
            ts = _format_ts(t.get("timestamp"))
            line = f"- {text}"
            if ctx:
                line += f" _(context: {ctx})_"
            if ts:
                line += f" _(recorded {ts})_"
            lines.append(line)
        lines.append("")
    lines.append("_Reflection prompts (personal growth):_")
    lines.append("")
    for i, prompt in enumerate(GROWTH_PROMPTS, 1):
        lines.append(f"{i}. {prompt}")

    if people:
        lines.extend(["", "## People mentioned", ""])
        for person in people:
            lines.append(f"- {person}")

    lines.extend(
        [
            "",
            "## Metadata",
            "",
            f"- **Total memories:** {total}",
            f"- **Generated:** {generated_at}",
        ]
    )
    for typ in MEMORY_TYPES:
        if counts.get(typ):
            lines.append(f"- **{typ}:** {counts[typ]}")
    lines.append("")
    return "\n".join(lines)


def _distinct_people(memories: Sequence[Mapping[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in memories:
        for field in ("person", "participants"):
            raw = (entry.get(field) or "").strip()
            if not raw:
                continue
            parts = [raw] if field == "person" else [p.strip() for p in raw.split(",")]
            for part in parts:
                if not part:
                    continue
                key = part.lower()
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(part)
    return ordered


class UserProfileExporter:
    """
    Plug-and-play exporter: build and optionally write the user profile markdown.

    Example
    -------
    exporter = UserProfileExporter()
    path = exporter.export(brain.get_memories_full(), persona=my_persona, thoughts=brain.get_thoughts(limit=20))
    context = exporter.agent_context_only(...)
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or os.path.dirname(os.path.abspath(__file__))

    @property
    def default_path(self) -> str:
        return default_profile_path(self.data_dir)

    def build(
        self,
        memories: Sequence[Mapping[str, Any]],
        persona: Any = None,
        thoughts: Optional[Sequence[Mapping[str, Any]]] = None,
        people: Optional[Sequence[str]] = None,
    ) -> str:
        return build_user_profile_markdown(memories, persona=persona, thoughts=thoughts, people=people)

    def agent_context_only(
        self,
        memories: Sequence[Mapping[str, Any]],
        persona: Any = None,
        people: Optional[Sequence[str]] = None,
        max_chars: int = 2800,
    ) -> str:
        persona_info = _persona_dict(persona)
        grouped = _group_memories(memories)
        if people is None:
            people = _distinct_people(memories)
        bullets = _agent_context_bullets(persona_info, grouped, people, max_chars=max_chars)
        return "\n".join(bullets)

    def export(
        self,
        memories: Sequence[Mapping[str, Any]],
        persona: Any = None,
        thoughts: Optional[Sequence[Mapping[str, Any]]] = None,
        people: Optional[Sequence[str]] = None,
        path: Optional[str] = None,
    ) -> str:
        """
        Write profile markdown to disk. Returns the path written.
        """
        out_path = os.path.abspath(path or self.default_path)
        content = self.build(memories, persona=persona, thoughts=thoughts, people=people)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        return out_path

    def extract_agent_context_from_file(self, path: Optional[str] = None) -> str:
        """Read an existing profile file and return only the Agent context section."""
        src = os.path.abspath(path or self.default_path)
        if not os.path.isfile(src):
            return ""
        with open(src, "r", encoding="utf-8") as f:
            text = f.read()
        match = re.search(
            r"## Agent context\s*\n+(.*?)(?:\n---\n|\n## )",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return ""
        block = match.group(1).strip()
        # Drop the italic instruction line
        lines = [
            ln
            for ln in block.splitlines()
            if ln.strip() and not ln.strip().startswith("_Copy from here")
        ]
        return "\n".join(lines).strip()
