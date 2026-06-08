import json
import os
import re
import time
import uuid

import ollama


MEMORY_TYPES = ("fact", "event", "preference", "habit", "belief", "relationship", "voice", "topic_style", "reaction")
DEFAULT_MEMORY_TYPE = "fact"
DEFAULT_SOURCE = "user"

# Optional fields for memory entries (person, topic, situation, role, participants)
MEMORY_OPTIONAL_FIELDS = ("person", "topic", "situation", "role", "participants")

# Max chars to send to reflection (avoids context overflow for long chats)
REFLECT_CONVERSATION_MAX_CHARS = 15000

# Labels the model may output when reflecting on a conversation (must match MEMORY_TYPES where used)
REFLECTION_LABELS = ("FACT:", "PREFERENCE:", "EVENT:", "HABIT:", "BELIEF:", "RELATIONSHIP:", "VOICE:", "TOPIC_STYLE:", "REACTION:")

DEFAULT_OLLAMA_MODEL = "llama3.1:8b"


def _data_dir():
    """Directory for persistent brain data (memory.json, thoughts.json)."""
    return os.path.dirname(os.path.abspath(__file__))


def _memory_path():
    return os.path.join(_data_dir(), "memory.json")


def _thoughts_path():
    return os.path.join(_data_dir(), "thoughts.json")


def _tidy_content_text(text):
    """Collapse runs of whitespace (including newlines) to a single space and strip. Makes stored content easy to read."""
    if not text or not isinstance(text, str):
        return ""
    return " ".join(text.split()).strip()


def _infer_person_from_relationship_content(content, model=DEFAULT_OLLAMA_MODEL):
    """
    Try to infer a person name from relationship memory content using Ollama LLM.
    Falls back to regex if model/unavailable.
    """
    if not content or not isinstance(content, str) or not content.strip():
        return ""
    content = content.strip()

    prompt = (
        "Extract the name of the other person from the following relationship-related sentence.\n"
        "If no name is present, return an empty string.\n"
        "Examples:\n"
        "Q: I am together with Chrissylia Phua\nA: Chrissylia Phua\n"
        "Q: I am in a relationship with David Lee\nA: David Lee\n"
        "Q: Sarah is my best friend\nA: Sarah\n"
        "Q: I am single\nA: \n"
        f"Q: {content}\nA:"
    )

    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"stop": ["\n"]}
        )
        answer = response.get("response", "")
        # Sanitize: only keep at most two capitalized words
        m = re.match(r"([A-Z][a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+(?:\s+[A-Z][a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+)?)", answer.strip())
        return m.group(1).strip() if m else ""
    except Exception:
        # Fallback to regex 
        m = re.search(r"(?:together with|with)\s+([A-Z][a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+(?:\s+[A-Z][a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+)?)", content)
        if m:
            return m.group(1).strip()
        m = re.match(r"^([A-Z][a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+(?:\s+[A-Z][a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+)?)\s+(?:is|and|'s|\()", content)
        if m:
            return m.group(1).strip()
        return ""

def _normalize_memory_content(content):
    """Return content as string; empty if not usable. Handles list/dict from malformed entries."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, (list, dict)):
        if isinstance(content, list) and len(content) > 0:
            authors = []
            for part in content:
                if isinstance(part, dict) and part.get("author"):
                    authors.append(part["author"])
            if authors:
                return f"Conversation between {', '.join(authors[:5])} (consolidated)."
        return "Conversation (consolidated)."
    return str(content).strip()


def _word_set(text):
    """Return set of normalized words (letters, numbers, apostrophe) from text, for similarity checks."""
    if not text or not isinstance(text, str):
        return set()
    return set(re.findall(r"[a-zA-Z0-9\u00C0-\u024F\u1E00-\u1EFF']+", text.lower()))


def _content_similarity(content1, content2):
    """Return Jaccard-like overlap (intersection size / min set size). 0 if either set empty."""
    w1, w2 = _word_set(content1), _word_set(content2)
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / min(len(w1), len(w2))


def _parse_conversation_event_participants_and_snippet(content):
    """
    Parse 'Conversation with A, B: rest' or 'Conversation with A, B (+N others): rest'.
    Returns (normalized_participants_tuple, snippet) for dedupe key, or (None, None) if not matched.
    normalized_participants is sorted tuple of participant names (lowercase, stripped).
    snippet is first 80 chars of the rest (after the colon), normalized.
    """
    if not content or not isinstance(content, str):
        return (None, None)
    text = content.strip()
    if not text.startswith("Conversation with "):
        return (None, None)
    prefix = "Conversation with "
    rest = text[len(prefix):].strip()
    if not rest:
        return (None, None)
    # Find first ": " to split participants from content
    colon = rest.find(": ")
    if colon <= 0:
        return (None, None)
    participants_part = rest[:colon].strip()
    body = rest[colon + 2:].strip()
    # participants_part can be "A, B" or "A, B (+2 others)"
    parts = [p.strip() for p in re.split(r",\s*", participants_part) if p.strip()]
    normalized = []
    for p in parts:
        if re.match(r"\(\+\d+\s+others\)", p, re.I):
            continue
        normalized.append(p.lower().strip())
    if not normalized:
        return (None, None)
    key_participants = tuple(sorted(normalized))
    snippet = _tidy_content_text(body)[:80] if body else ""
    return (key_participants, snippet)


def _is_noisy_event_content(content):
    """True if content looks like a single raw message line or just sender+timestamp (noisy)."""
    if not content or len(content) < 10:
        return False
    if isinstance(content, str):
        text = content.strip()
    else:
        text = _normalize_memory_content(content)
    if not text:
        return False
    # Keep summary-style events (see also stricter truncation check below for "Conversation with ")
    if text.startswith("Conversation with ") and len(text) > 50:
        # Stricter: treat truncated raw dumps as noisy (end with "...", short body, no sentence boundary)
        if text.endswith("...") and len(text) <= 180:
            body_start = text.find(": ") + 2 if ": " in text else 0
            body = text[body_start:].strip() if body_start else ""
            if len(body) <= 120 and body.endswith("..."):
                return True
        else:
            return False
    # Noisy: only "Name, [timestamp]" or similar
    if re.search(r"^[^[]+[,\-]\s*\[\d", text) and len(text) < 80 and "\n" not in text:
        return True
    if re.search(r"^[^[]+[,\-]\s*\[\d", text) and text.count("\n") <= 1:
        after = text.split("\n", 1)[-1].strip() if "\n" in text else ""
        if len(after) < 4:
            return True
    # "Name, [date]\n\nshort message"
    if "\n\n" in text:
        parts = text.split("\n\n", 1)
        if len(parts) == 2 and parts[0].strip() and re.search(r"\[\d", parts[0]):
            msg = parts[1].strip()
            if len(msg) < 4 or msg in ("", "Okie", "yas", "Hehe", "Lol", "Mew", "mewww", "okiee", "yesh"):
                return True
            if "\n" not in parts[1] and len(msg) < 60:
                return True
    return False


class SmartPersonaBrain:
    ####################################################################
    # === Initialization and State ===
    ####################################################################
    def __init__(self, persist=True, model=None):
        self.ollama_client = ollama.Client()
        env_model = (os.getenv("SMARTPERSONA_OLLAMA_MODEL") or "").strip()
        if model is not None and str(model).strip():
            self.model = str(model).strip()
        elif env_model:
            self.model = env_model
        else:
            self.model = DEFAULT_OLLAMA_MODEL
        self.state = {}
        self._memory = []  # list of { type, content, timestamp, source }
        self._thoughts = []  # list of { id, thought, context, timestamp }
        self._reflections = []  # list of reflection summary strings
        self._persist = persist
        self._thought_id_to_index = {}  # id -> index in _thoughts
        if self._persist:
            self._load_memory()
            self._load_thoughts()

    def get_state(self):
        """Get the state of the SmartPersona brain."""
        return self.state

    def get_model(self):
        """Active Ollama model name used for all chat calls."""
        return self.model

    def set_model(self, name):
        """Set the active Ollama model name (must be non-empty)."""
        n = (name or "").strip()
        if not n:
            raise ValueError("Model name cannot be empty")
        self.model = n

    def list_local_models(self):
        """
        Return sorted unique model names reported by the local Ollama daemon.
        Returns [] if Ollama is unreachable or listing fails.
        """
        try:
            r = self.ollama_client.list()
            models = getattr(r, "models", None)
            if models is None and isinstance(r, dict):
                models = r.get("models")
            if not models:
                return []
            out = []
            for m in models:
                if hasattr(m, "model"):
                    name = getattr(m, "model", None) or ""
                elif isinstance(m, dict):
                    name = m.get("model") or m.get("name") or ""
                else:
                    name = str(m)
                name = (name or "").strip()
                if name:
                    out.append(name)
            return sorted(set(out), key=lambda x: x.lower())
        except Exception:
            return []

    def ping_model(self, model=None):
        """
        Verify that Ollama responds for the given model (or the active model).
        Returns {"ok": True} or {"ok": False, "error": str}.
        """
        m = (model or self.model or "").strip()
        if not m:
            return {"ok": False, "error": "No model specified"}
        try:
            self.ollama_client.chat(
                model=m,
                messages=[{"role": "user", "content": "."}],
                options={"num_predict": 2},
            )
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    ####################################################################
    # === Memory Loading, Saving, Normalization, and Maintenance ===
    ####################################################################

    def _load_memory(self):
        path = _memory_path()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._memory = json.load(f)
                self._sanitize_memory()
            except (json.JSONDecodeError, OSError):
                self._memory = []

    def _save_memory(self):
        if not self._persist:
            return
        path = _memory_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._memory, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _sanitize_memory(self):
        """
        Clean memory in-place: normalize content to string, drop empty, deduplicate,
        remove noisy single-message events. Saves if anything changed.
        """
        if not isinstance(self._memory, list):
            self._memory = []
            return
        seen = {}
        event_conversation_seen = {}  # (normalized_participants, snippet) -> index in kept
        kept = []
        for entry in self._memory:
            if not isinstance(entry, dict):
                continue
            raw = entry.get("content")
            content = _normalize_memory_content(raw)
            typ = entry.get("type", "fact")
            source = entry.get("source", "")
            if typ not in MEMORY_TYPES:
                typ = DEFAULT_MEMORY_TYPE
            if not content:
                continue
            person = (entry.get("person") or "").strip() if isinstance(entry.get("person"), str) else ""
            # Event + message_history: dedupe by normalized participants + snippet (same conversation, different sender order)
            if typ == "event" and source == "message_history":
                participants_key, snippet = _parse_conversation_event_participants_and_snippet(content)
                if participants_key is not None and snippet:
                    conv_key = (participants_key, snippet)
                    if conv_key in event_conversation_seen:
                        continue
                    event_conversation_seen[conv_key] = len(kept)
            key = (typ, content.lower(), person if typ == "relationship" else "")
            if key in seen:
                continue
            seen[key] = len(kept)
            if typ == "event" and source == "message_history" and _is_noisy_event_content(content):
                continue
            content = _tidy_content_text(content)
            if not content:
                continue
            kept.append({
                "type": typ,
                "content": content,
                "timestamp": entry.get("timestamp"),
                "source": entry.get("source"),
            })
            for k in ("timestamp_start", "timestamp_end", "summary", "person", "topic", "situation", "role", "participants"):
                if k in entry and k not in kept[-1]:
                    kept[-1][k] = entry[k]
        if len(kept) != len(self._memory):
            self._memory = kept
            self._save_memory()

    def _deduplicate_relationship_memories(self):
        """
        Deduplicate relationship memories: same person + same/similar content → keep one.
        - Same content: keep the one with Person set (or set person from inferred).
        - Content A is substring of content B: keep B only.
        - Same person, contents share 3+ words: keep only the longest (merge near-duplicates).
        Modifies _memory in place and saves if changed.
        """
        if not isinstance(self._memory, list):
            return
        non_relationship = [e for e in self._memory if e.get("type") != "relationship"]
        relationship = [e for e in self._memory if e.get("type") == "relationship"]
        if not relationship:
            return

        def norm(s):
            return (s or "").strip()

        def person_key(entry):
            p = norm(entry.get("person") or "")
            if not p:
                p = _infer_person_from_relationship_content(
                    _normalize_memory_content(entry.get("content"))
                )
            return p.lower() if p else "__no_person__"

        def words(s):
            return set(re.findall(r"[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF']+", (s or "").lower()))

        # Group by person
        by_person = {}
        for entry in relationship:
            content = _tidy_content_text(_normalize_memory_content(entry.get("content")))
            if not content:
                continue
            key = person_key(entry)
            if key not in by_person:
                by_person[key] = []
            # Ensure we have a copy so we can set person later
            e = dict(entry)
            e["content"] = content
            if not norm(e.get("person") or ""):
                inferred = _infer_person_from_relationship_content(content)
                if inferred:
                    e["person"] = inferred
            by_person[key].append(e)

        kept_entries = []
        for key, entries in by_person.items():
            # Same content: keep one, prefer with person set
            seen_content = {}
            for e in entries:
                c = e["content"]
                c_lower = c.lower()
                if c_lower in seen_content:
                    existing = seen_content[c_lower]
                    if norm(e.get("person") or "") and not norm(existing.get("person") or ""):
                        seen_content[c_lower] = e
                else:
                    seen_content[c_lower] = e
            entries = list(seen_content.values())

            # Sort by content length descending
            entries.sort(key=lambda x: len(x["content"]), reverse=True)
            kept_for_person = []
            for e in entries:
                content = e["content"]
                content_lower = content.lower()
                # Drop if this content is a substring of any already kept
                if any(content_lower in (k["content"].lower()) for k in kept_for_person if k["content"] != content):
                    continue
                # If any kept is a substring of this, remove it (we process longest first so rarely needed)
                kept_for_person = [k for k in kept_for_person if k["content"].lower() not in content_lower or k["content"] == content]
                # If this shares 3+ words with any kept, keep only the longer (we're desc by length so this one is longer or equal)
                w = words(content)
                merged = False
                for k in kept_for_person[:]:
                    if len(w & words(k["content"])) >= 3:
                        if len(content) >= len(k["content"]):
                            kept_for_person.remove(k)
                        else:
                            merged = True
                            break
                if not merged:
                    kept_for_person.append(e)
            kept_entries.extend(kept_for_person)

        self._memory = non_relationship + kept_entries
        self._save_memory()

    def _deduplicate_reflection_style_memories(self):
        """
        One-time style: merge near-duplicate topic_style, reaction, preference entries
        (same type + topic/situation/person and high content similarity). Keeps one per group (longest content).
        """
        if not isinstance(self._memory, list):
            return
        rest = [m for m in self._memory if m.get("type") not in ("topic_style", "reaction", "preference")]
        target = [m for m in self._memory if m.get("type") in ("topic_style", "reaction", "preference")]
        if not target:
            return

        def key(entry):
            t = entry.get("type", "")
            return (
                t,
                (entry.get("topic") or "").strip().lower(),
                (entry.get("situation") or "").strip().lower(),
                (entry.get("person") or "").strip().lower(),
            )

        groups = {}
        for m in target:
            k = key(m)
            if k not in groups:
                groups[k] = []
            groups[k].append(m)

        kept = []
        for k, entries in groups.items():
            entries.sort(key=lambda m: len((m.get("content") or "")), reverse=True)
            kept_in_group = []
            for e in entries:
                content = _tidy_content_text(_normalize_memory_content(e.get("content")))
                if not content:
                    continue
                if any(_content_similarity(content, (k2.get("content") or "")) >= 0.5 for k2 in kept_in_group):
                    continue
                kept_in_group.append(e)
            kept.extend(kept_in_group)

        self._memory = rest + kept
        self._save_memory()

    def _consolidate_conversation_events(self, time_window_seconds=86400):
        """
        Merge consecutive message_history events with the same normalized participants and close timestamps
        into one event with timestamp_start, timestamp_end, and a short summary. time_window_seconds: max gap to merge (default 24h).
        """
        if not isinstance(self._memory, list) or len(self._memory) < 2:
            return
        result = []
        i = 0
        while i < len(self._memory):
            entry = self._memory[i]
            if entry.get("type") != "event" or entry.get("source") != "message_history":
                result.append(entry)
                i += 1
                continue
            # Collect consecutive event+message_history entries
            run = []
            while i < len(self._memory):
                e = self._memory[i]
                if e.get("type") != "event" or e.get("source") != "message_history":
                    break
                run.append(e)
                i += 1
            if not run:
                continue
            # Group consecutive same-participant events within time window (preserve order)
            to_merge = [run[0]]
            for e in run[1:]:
                content_prev = _normalize_memory_content(to_merge[-1].get("content"))
                content_cur = _normalize_memory_content(e.get("content"))
                part_prev, _ = _parse_conversation_event_participants_and_snippet(content_prev)
                part_cur, _ = _parse_conversation_event_participants_and_snippet(content_cur)
                t_prev = to_merge[-1].get("timestamp") or 0
                t_cur = e.get("timestamp") or 0
                if part_prev == part_cur and part_cur is not None and abs(t_cur - t_prev) <= time_window_seconds:
                    to_merge.append(e)
                else:
                    if len(to_merge) >= 2:
                        result.append(self._merge_conversation_events(to_merge))
                    else:
                        result.append(to_merge[0])
                    to_merge = [e]
            if len(to_merge) >= 2:
                result.append(self._merge_conversation_events(to_merge))
            else:
                result.append(to_merge[0])

        if len(result) != len(self._memory):
            self._memory = result
            self._save_memory()

    def _merge_conversation_events(self, entries):
        """Build a single event from a list of same-participant message_history events."""
        entries = sorted(entries, key=lambda e: (e.get("timestamp") or 0))
        first = entries[0]
        last = entries[-1]
        content = _normalize_memory_content(first.get("content"))
        part_key, _ = _parse_conversation_event_participants_and_snippet(content)
        participants_str = ", ".join(part_key) if part_key and part_key != ("__unknown__",) else (first.get("participants") or "")
        first_body = content.split(": ", 1)[-1].strip() if ": " in content else content
        summary_body = first_body[:120] + ("..." if len(first_body) > 120 else "")
        if len(entries) > 1:
            last_content = _normalize_memory_content(last.get("content"))
            last_body = last_content.split(": ", 1)[-1].strip() if ": " in last_content else last_content
            summary_body = summary_body + " ... " + (last_body[:80] + "..." if len(last_body) > 80 else last_body)
        merged_content = f"Conversation with {participants_str}: {summary_body}" if participants_str else summary_body
        ts_start = min((e.get("timestamp") or 0) for e in entries)
        ts_end = max((e.get("timestamp") or 0) for e in entries)
        out = {
            "type": "event",
            "content": _tidy_content_text(merged_content),
            "timestamp": ts_start,
            "source": "message_history",
            "timestamp_start": ts_start,
            "timestamp_end": ts_end,
            "summary": f"{len(entries)} messages",
        }
        if participants_str:
            out["participants"] = participants_str
        if len(entries) == 1 and entries[0].get("person"):
            out["person"] = entries[0]["person"]
        return out

    def tidy_memory(self):
        """
        Public API: run sanitization (dedupe, drop empty, drop noisy events), then
        relationship-specific deduplication, then reflection-style (topic_style/reaction/preference) near-dedupe,
        then consolidate consecutive same-participant conversation events.
        Call this when the user requests a refresh/tidy of memory.
        """
        self._sanitize_memory()
        self._deduplicate_relationship_memories()
        self._deduplicate_reflection_style_memories()
        self._consolidate_conversation_events()

    def review_memories_for_clarification(self, memory_limit=50):
        """
        Ask the model to review current memories and suggest questions to clarify
        ambiguities, gaps, or inconsistencies. Returns a list of question strings (may be empty).
        """
        memory_context = self._build_memory_context(limit=memory_limit)
        if not memory_context.strip():
            return []
        prompt = (
            "Given the following memories about the user, what is ambiguous, inconsistent, or missing?\n"
            "Reply with 1-5 short questions you would ask the user to clarify. One question per line, "
            "each ending with a question mark. Do not add any intro line like 'Here are 5 questions'—only the questions.\n"
            "If nothing needs clarification, reply with only the word: NONE\n\n"
            + memory_context
        )
        try:
            resp = self.ollama_client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            return []
        raw = self._extract_message_content(resp)
        if not raw or "NONE" in raw.strip().upper().split():
            return []
        # Skip intro lines the model often outputs (e.g. "Here are 5 questions to clarify...")
        intro_patterns = (
            r"^here\s+are\s+\d*\s*questions",
            r"^here\s+is\s+(?:a\s+)?(?:list\s+of\s+)?\d*\s*questions",
            r"^the\s+following\s+questions",
            r"^below\s+are",
            r"^questions\s+to\s+clarify",
            r"^list\s+of\s+questions",
            r"^clarification\s+questions",
        )
        questions = []
        for line in raw.split("\n"):
            line = line.strip()
            line = line.lstrip("-•* 123456789.) ").strip()  # strip leading list markers
            if not line or len(line) <= 5 or "NONE" in line.upper():
                continue
            if not re.search(r"\?$", line):
                # Not question-shaped; skip if it looks like intro meta-text
                lower = line.lower()
                if any(re.search(p, lower) for p in intro_patterns):
                    continue
            questions.append(line)
        return questions[:10]

    def validate_memory_entry(
        self,
        content,
        type=DEFAULT_MEMORY_TYPE,
        person=None,
        topic=None,
        situation=None,
        role=None,
        memory_limit=15,
    ):
        """
        Ask the AI to validate a proposed memory: does it fit the type, and does it
        duplicate or conflict with existing memories? Returns {"valid": bool, "feedback": str}.
        """
        empty = {"valid": True, "feedback": ""}
        if not content or not content.strip():
            return empty
        type = type if type in MEMORY_TYPES else DEFAULT_MEMORY_TYPE
        memory_context = self._build_memory_context(limit=memory_limit)
        parts = [
            f"Proposed new memory:",
            f"  Type: {type}",
            f"  Content: {content.strip()}",
        ]
        if person:
            parts.append(f"  Person: {person}")
        if topic:
            parts.append(f"  Topic: {topic}")
        if situation:
            parts.append(f"  Situation: {situation}")
        if role:
            parts.append(f"  Role: {role}")
        prompt = (
            "Check this proposed memory.\n\n"
            + "\n".join(parts)
            + "\n\n"
            + ("Existing memories (for overlap check):\n" + memory_context if memory_context else "")
            + "\n\n"
            "Reply with VALID if the memory fits the type and does not duplicate existing knowledge. "
            "Otherwise reply with ISSUES: followed by a short list of issues (e.g. wrong type, duplicate, unclear). "
            "One line for VALID or ISSUES: ..."
        )
        try:
            resp = self.ollama_client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            return empty
        raw = self._extract_message_content(resp)
        if not raw:
            return empty
        raw_upper = raw.strip().upper()
        if raw_upper.startswith("VALID") and ("ISSUES" not in raw_upper[:20]):
            return {"valid": True, "feedback": raw.strip()}
        if raw_upper.startswith("ISSUES:"):
            return {"valid": False, "feedback": raw.strip()[7:].strip() or raw.strip()}
        return {"valid": False, "feedback": raw.strip()}

    ####################################################################
    # === Memory Management & Query ===
    ####################################################################

    def add_memory(
        self,
        content,
        type=DEFAULT_MEMORY_TYPE,
        source=DEFAULT_SOURCE,
        skip_duplicate=True,
        person=None,
        topic=None,
        situation=None,
        role=None,
        participants=None,
    ):
        """
        Add a memory. type one of: fact, event, preference, habit, belief, relationship, voice, topic_style, reaction.
        If skip_duplicate is True (default), skips adding when the same content already exists
        for this type (normalized by stripping and lowercasing), to avoid reflection duplicates.
        Optional: person, topic, situation, role, participants for richer context and filtering.
        """
        if type not in MEMORY_TYPES:
            type = DEFAULT_MEMORY_TYPE
        text = _normalize_memory_content(content)
        if not text:
            return
        if skip_duplicate and source == "reflection":
            key = text.lower()
            for m in self._memory:
                if m.get("type") != type:
                    continue
                if (m.get("content") or "").strip().lower() != key:
                    continue
                if type == "relationship" and person:
                    if (m.get("person") or "").strip().lower() != (person or "").strip().lower():
                        continue
                return
            # Fuzzy dedupe for topic_style, reaction, preference: skip if same type + same topic/situation/person and high content overlap
            if type in ("topic_style", "reaction", "preference"):
                norm_topic = (topic or "").strip().lower()
                norm_situation = (situation or "").strip().lower()
                norm_person = (person or "").strip().lower()
                for m in self._memory:
                    if m.get("type") != type:
                        continue
                    if (m.get("topic") or "").strip().lower() != norm_topic:
                        continue
                    if (m.get("situation") or "").strip().lower() != norm_situation:
                        continue
                    if (m.get("person") or "").strip().lower() != norm_person:
                        continue
                    if _content_similarity(text, (m.get("content") or "")) >= 0.5:
                        return
        entry = {
            "type": type,
            "content": text,
            "timestamp": time.time(),
            "source": source,
        }
        if person is not None and str(person).strip():
            entry["person"] = str(person).strip()
        if topic is not None and str(topic).strip():
            entry["topic"] = str(topic).strip()
        if situation is not None and str(situation).strip():
            entry["situation"] = str(situation).strip()
        if role is not None and str(role).strip():
            entry["role"] = str(role).strip()
        if participants is not None and str(participants).strip():
            entry["participants"] = str(participants).strip()
        self._memory.append(entry)
        self._save_memory()

    def get_memories(self, type=None, limit=20, person=None, persons=None):
        """
        Get memories, optionally filtered by type and/or person(s). Most recent last; return last `limit` items.
        If persons is a non-empty list, include entries that mention any of those names (person field or participants).
        Else if person is set (string), include only entries where entry has person equal to that, or participants list contains that name (case-insensitive).
        """
        subset = self._memory
        if type is not None and type in MEMORY_TYPES:
            subset = [m for m in subset if m.get("type") == type]

        needles_multi = []
        if persons is not None:
            needles_multi = [p.strip().lower() for p in persons if (p or "").strip()]

        if needles_multi:

            def mentions_any(m):
                for needle in needles_multi:
                    if (m.get("person") or "").strip().lower() == needle:
                        return True
                    for p in (m.get("participants") or "").split(","):
                        if (p or "").strip().lower() == needle:
                            return True
                return False

            subset = [m for m in subset if mentions_any(m)]
        elif person is not None and str(person).strip():
            needle = str(person).strip().lower()

            def mentions_person(m):
                if (m.get("person") or "").strip().lower() == needle:
                    return True
                parts = (m.get("participants") or "").split(",")
                for p in parts:
                    if (p or "").strip().lower() == needle:
                        return True
                return False

            subset = [m for m in subset if mentions_person(m)]
        return subset[-limit:] if limit else subset

    def list_people_in_memory(self):
        """Distinct names from memory person fields and participants lists (stable order, first-seen casing)."""
        seen = set()
        ordered = []
        for m in self._memory:
            p = (m.get("person") or "").strip()
            if p and p.lower() not in seen:
                seen.add(p.lower())
                ordered.append(p)
            for part in (m.get("participants") or "").split(","):
                part = part.strip()
                if part and part.lower() not in seen:
                    seen.add(part.lower())
                    ordered.append(part)
        return ordered

    def get_memory(self):
        """Backward compatibility: return full flat list of memory entries (content only, as strings)."""
        return [_normalize_memory_content(m.get("content")) for m in self._memory]

    def add_habit(self, habit):
        """
        Add a habit (memory type habit) and optionally tidy/group habits via the model.
        Replaces standalone PersonaHabits: habits are stored as memories and can be tidied.
        """
        self.add_memory(habit.strip(), type="habit", source=DEFAULT_SOURCE)
        habits = [m["content"] for m in self.get_memories(type="habit", limit=100)]
        if len(habits) <= 1:
            return
        prompt = (
            "Given the following list of habits, group similar ones and tidy the descriptions. "
            "Reply with only the list, one habit per line, each line starting with '- '."
        ) + "\n\n" + "\n".join(f"- {h}" for h in habits)
        resp = self.generate_response(prompt, include_memory=False, include_recent_thoughts=False)
        if isinstance(resp, dict) and "message" in resp and "content" in resp["message"]:
            text = resp["message"]["content"]
            new_habits = [line.strip().lstrip("- ").strip() for line in text.split("\n") if line.strip()]
            if new_habits:
                self._memory = [m for m in self._memory if m["type"] != "habit"]
                for h in new_habits:
                    self._memory.append({
                        "type": "habit",
                        "content": h,
                        "timestamp": time.time(),
                        "source": DEFAULT_SOURCE,
                    })
                self._save_memory()

    def get_habits(self):
        """Get habit contents (backward compatible with PersonaHabits)."""
        return [m["content"] for m in self.get_memories(type="habit", limit=100)]

    ####################################################################
    # === Thoughts Management ===
    ####################################################################

    def _load_thoughts(self):
        path = _thoughts_path()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._thoughts = json.load(f)
                self._sanitize_thoughts()
            except (json.JSONDecodeError, OSError):
                self._thoughts = []
                self._thought_id_to_index = {}

    def _save_thoughts(self):
        if not self._persist:
            return
        path = _thoughts_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._thoughts, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _sanitize_thoughts(self):
        """
        Clean persisted thoughts in-place so malformed entries do not break lookup.
        Keeps the append-only thought shape: {id, thought, context, timestamp}.
        """
        if not isinstance(self._thoughts, list):
            self._thoughts = []
            self._thought_id_to_index = {}
            self._save_thoughts()
            return

        changed = False
        seen_ids = set()
        kept = []
        for entry in self._thoughts:
            if not isinstance(entry, dict):
                changed = True
                continue

            thought = entry.get("thought")
            thought = thought if isinstance(thought, str) else str(thought) if thought is not None else ""
            thought = thought.strip()
            if not thought:
                changed = True
                continue

            thought_id = str(entry.get("id") or uuid.uuid4()).strip()
            if not thought_id or thought_id in seen_ids:
                thought_id = str(uuid.uuid4())
                changed = True
            seen_ids.add(thought_id)

            context = entry.get("context", "")
            context = context if isinstance(context, str) else str(context) if context is not None else ""

            timestamp = entry.get("timestamp")
            try:
                timestamp = float(timestamp)
            except (TypeError, ValueError):
                timestamp = time.time()
                changed = True

            clean = {
                "id": thought_id,
                "thought": thought,
                "context": context,
                "timestamp": timestamp,
            }
            if clean != entry:
                changed = True
            kept.append(clean)

        self._thoughts = kept
        self._thought_id_to_index = {t["id"]: i for i, t in enumerate(self._thoughts)}
        if changed:
            self._save_thoughts()

    def record_thought(self, thought, context=""):
        """Record a thought with optional context. Returns the thought id."""
        tid = str(uuid.uuid4())
        entry = {
            "id": tid,
            "thought": thought if isinstance(thought, str) else str(thought),
            "context": context if isinstance(context, str) else str(context),
            "timestamp": time.time(),
        }
        self._thoughts.append(entry)
        self._thought_id_to_index[tid] = len(self._thoughts) - 1
        self._save_thoughts()
        return tid

    def get_thoughts(self, limit=10):
        """Get the most recent thoughts (last `limit`)."""
        return self._thoughts[-limit:] if limit else list(self._thoughts)

    def reconsider(self, thought_id, new_context):
        """
        Reconsider a prior thought given new context. Retrieves the thought, asks the model
        to reconsider, and appends the new thought (append-only, brain-like).
        Returns the new thought id.
        """
        idx = self._thought_id_to_index.get(thought_id)
        if idx is None:
            raise ValueError(f"Unknown thought id: {thought_id}")
        prior = self._thoughts[idx]
        prompt = (
            "Previously you thought:\n"
            + prior["thought"]
            + "\n\nContext then: "
            + (prior["context"] or "(none)")
            + "\n\nNew context: "
            + str(new_context)
            + "\n\nReconsider and give your updated view in a short paragraph."
        )
        resp = self.ollama_client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        new_thought = ""
        if isinstance(resp, dict) and "message" in resp and "content" in resp["message"]:
            new_thought = resp["message"]["content"].strip()
        return self.record_thought(new_thought, context=f"Reconsideration of thought {thought_id}; new context: {new_context}")

    ####################################################################
    # === Memory/Thoughts Context Builders ===
    ####################################################################

    def _build_memory_context(self, limit=20, type=None, person=None, persons=None):
        """Build a string of recent memories for injection into prompts. If persons is set (non-empty list), filter to entries mentioning any of those names. Else if person is set, filter to that name."""
        memories = self.get_memories(type=type, limit=limit, person=person, persons=persons)
        if not memories:
            return ""
        lines = []
        for m in memories:
            content = _normalize_memory_content(m.get("content"))
            if m.get("person"):
                lines.append(f"- Relationship with {m['person']}: {content}")
            elif m.get("participants"):
                lines.append(f"- Conversation with {m['participants']}: {content}")
            elif m.get("topic"):
                lines.append(f"- Topic [{m['topic']}]: {content}")
            elif m.get("situation"):
                lines.append(f"- When [{m['situation']}]: {content}")
            else:
                lines.append(f"- [{m['type']}] {content}")
        return "What you remember:\n" + "\n".join(lines)

    def _build_thoughts_context(self, limit=10):
        """Build a string of recent thoughts for injection into prompts."""
        thoughts = self.get_thoughts(limit=limit)
        if not thoughts:
            return ""
        lines = []
        for t in thoughts:
            lines.append(f"- {t['thought']}")
        return "Recent thoughts:\n" + "\n".join(lines)

    ####################################################################
    # === Reflection and Reasoning ===
    ####################################################################

    def reflect_on_events(self, events_summary, conversation_participants=None):
        """
        Reflect on what happened. Asks the model what to remember; parses and adds to memory.
        If conversation_participants is set (list of names), skips adding reflection EVENT lines
        that are redundant with the just-stored conversation summary event (same participants).
        Returns the raw reflection text and any added memories.
        """
        memory_context = self._build_memory_context(limit=30)
        prompt = (
            "Given the conversation below, list what should be remembered. Use exactly these labels, one per line:\n"
            "FACT: <something that is true>\n"
            "PREFERENCE: <a preference>\n"
            "EVENT: <something that happened>\n"
            "HABIT: <a habit>\n"
            "BELIEF: <a belief or value>\n"
            "RELATIONSHIP: <Person>: <description of relationship with that person>\n"
            "VOICE: <how the person talks - phrases, tone, slang, formality>\n"
            "TOPIC_STYLE: <topic>: <how they reply in that context> or just <description>\n"
            "REACTION: <situation>: <how they react> or just <description>\n"
            "Only list real items from the conversation. Do NOT write lines like 'PREFERENCE: None mentioned' or 'HABIT: None specified'. If there is nothing to add, reply with only the word: NONE\n\n"
            "Conversation:\n\n"
            + events_summary
            + "\n\n"
            + (memory_context if memory_context else "")
        )
        resp = self.ollama_client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = self._extract_message_content(resp)
        added = []
        if raw and "NONE" not in raw.upper().split():
            for line in raw.split("\n"):
                line = line.strip()
                for prefix in REFLECTION_LABELS:
                    idx = line.upper().find(prefix)
                    if idx >= 0:
                        rest = line[idx + len(prefix) :].strip()
                        if not rest or self._is_filler_reflection(rest):
                            break
                        kind = prefix.rstrip(":").lower()
                        if kind not in MEMORY_TYPES:
                            break
                        content = rest
                        person = topic = situation = None
                        if kind == "relationship" and ":" in rest:
                            part1, _, part2 = rest.partition(":")
                            person = part1.strip()
                            content = part2.strip()
                        elif kind == "topic_style" and ":" in rest:
                            part1, _, part2 = rest.partition(":")
                            topic = part1.strip()
                            content = part2.strip()
                        elif kind == "reaction" and ":" in rest:
                            part1, _, part2 = rest.partition(":")
                            situation = part1.strip()
                            content = part2.strip()
                        if content and not self._is_filler_reflection(content):
                            # Skip adding EVENT if it's redundant with the conversation summary we just stored
                            if kind == "event" and conversation_participants:
                                recent = [m for m in self._memory[-10:] if m.get("type") == "event" and m.get("source") == "message_history"]
                                part_set = set((p or "").strip().lower() for p in conversation_participants if p)
                                for m in reversed(recent):
                                    p_str = (m.get("participants") or "").strip()
                                    if not p_str:
                                        continue
                                    existing = set((x.strip().lower() for x in p_str.split(",") if x.strip()))
                                    if part_set and existing and part_set == existing:
                                        break  # skip adding this EVENT
                                else:
                                    self.add_memory(
                                        content,
                                        type=kind,
                                        source="reflection",
                                        person=person,
                                        topic=topic,
                                        situation=situation,
                                    )
                                    added.append({"type": kind, "content": content, "person": person, "topic": topic, "situation": situation})
                            else:
                                self.add_memory(
                                    content,
                                    type=kind,
                                    source="reflection",
                                    person=person,
                                    topic=topic,
                                    situation=situation,
                                )
                                added.append({"type": kind, "content": content, "person": person, "topic": topic, "situation": situation})
                        break
        self._reflections.append(raw[:500] if raw else "")
        return {"reflection": raw, "added_memories": added}

    def reflect_on_conversation(self, messages_or_summary, conversation_participants=None):
        """
        Reflect on a conversation (string summary or list of message strings).
        Converts to a summary if needed, then calls reflect_on_events.
        conversation_participants: optional list of participant names (for skipping redundant EVENTs).
        """
        if isinstance(messages_or_summary, list):
            summary = "\n".join(str(m) for m in messages_or_summary)
        else:
            summary = str(messages_or_summary)
        return self.reflect_on_events(summary, conversation_participants=conversation_participants)

    def think(self, prompt, persona_role=None):
        """
        Think about a prompt, optionally from the perspective of a specific persona role.
        Does not use memory or recent thoughts. Returns the model's text or None.
        """
        if persona_role:
            prompt = f"You are acting as: {persona_role}\nThink about the following prompt: {prompt}"
        else:
            prompt = f"Think about the following prompt: {prompt}"
        resp = self.generate_response(prompt, include_memory=False, include_recent_thoughts=False)
        return self._extract_message_content(resp) or None

    def _consider_validated(
        self,
        prompt,
        positive_question,
        negative_question,
        memory_limit=20,
        thoughts_limit=10,
    ):
        """
        Internal: ask the model a positive and a negative question about the prompt,
        with memory/thoughts context. Returns {"positive": str or None, "negative": str or None}.
        """
        resp_pos = self.generate_response(
            f"{positive_question}\n\nPrompt:\n{prompt}",
            include_memory=True,
            include_recent_thoughts=True,
            memory_limit=memory_limit,
            thoughts_limit=thoughts_limit,
        )
        resp_neg = self.generate_response(
            f"{negative_question}\n\nPrompt:\n{prompt}",
            include_memory=True,
            include_recent_thoughts=True,
            memory_limit=memory_limit,
            thoughts_limit=thoughts_limit,
        )
        return {
            "positive": self._extract_message_content(resp_pos) or None,
            "negative": self._extract_message_content(resp_neg) or None,
        }

    def consider_what_to_do_validated(self, prompt, memory_limit=20, thoughts_limit=10):
        """
        Consider what to do about a prompt and validate against what not to do.
        Returns {"to_do": ..., "not_to_do": ...}. Uses memory and recent thoughts.
        """
        result = self._consider_validated(
            prompt,
            "What are appropriate or effective actions to take in the following situation? Suggest what to do.",
            "Considering the following situation or prompt, what are actions or responses that should be avoided or not taken? Please provide a brief explanation if possible.",
            memory_limit=memory_limit,
            thoughts_limit=thoughts_limit,
        )
        return {"to_do": result["positive"], "not_to_do": result["negative"]}

    def consider_what_to_say(self, prompt, memory_limit=20, thoughts_limit=10):
        """
        Consider what to say in response to a prompt and validate against what not to say.
        Returns {"to_say": ..., "not_to_say": ...}. Uses memory and recent thoughts.
        """
        result = self._consider_validated(
            prompt,
            "What is an appropriate or effective thing to say in the following situation? Suggest the best reply or statement.",
            "Considering the following situation or prompt, what are things that should NOT be said or replied? Please provide a brief explanation if possible.",
            memory_limit=memory_limit,
            thoughts_limit=thoughts_limit,
        )
        return {"to_say": result["positive"], "not_to_say": result["negative"]}

    ####################################################################
    # === Teaching / Message Ingestion & Parsing ===
    ####################################################################

    def teach_from_message_history(
        self,
        message_history,
        format="auto",
        auto_reflect=True,
        store_conversation_summary=True,
    ):
        """
        Teach the brain from message history between user and others.
        """
        if format == "auto":
            format = self._detect_message_format(message_history)

        parsed = self._parse_message_history(message_history, format)

        if not parsed:
            return {
                "processed": 0,
                "reflection": None,
                "summary": "No messages to process",
                "conversation_memory_added": False,
            }

        conversation_text = self._format_conversation_for_reflection(parsed)

        result = {
            "processed": len(parsed),
            "reflection": None,
            "summary": "",
            "conversation_memory_added": False,
        }
        participants = None

        if store_conversation_summary and conversation_text:
            summary_content, participants = self._make_conversation_summary_memory(parsed, conversation_text)
            if summary_content:
                person = participants[0] if len(participants) == 1 else None
                self.add_memory(
                    summary_content,
                    type="event",
                    source="message_history",
                    skip_duplicate=False,
                    person=person,
                    participants=", ".join(participants) if participants else None,
                )
                result["conversation_memory_added"] = True

        if auto_reflect:
            text_for_reflection = self._truncate_for_reflection(conversation_text)
            reflection_result = self.reflect_on_conversation(text_for_reflection, conversation_participants=participants if summary_content else None)
            result["reflection"] = reflection_result

            added = reflection_result.get("added_memories", [])
            if added:
                by_type = {}
                for mem in added:
                    mem_type = mem.get("type", "unknown")
                    by_type[mem_type] = by_type.get(mem_type, 0) + 1
                parts = [f"{count} {mem_type}(s)" for mem_type, count in by_type.items()]
                result["summary"] = f"Learned: {', '.join(parts)}"
            else:
                result["summary"] = "No new memories extracted from this conversation"
                if len(parsed) > 200:
                    result["summary"] += ". Tip: For very long chats the model sees a shortened version (start + end); the conversation was still stored as an event."
            if result.get("conversation_memory_added"):
                result["summary"] += " (conversation stored as event)"
        else:
            result["summary"] = f"Processed {len(parsed)} messages (reflection disabled)"
            if result.get("conversation_memory_added"):
                result["summary"] += "; conversation stored as event"

        if conversation_text and conversation_text.strip():
            result["conversation_review"] = self.review_conversation_emotions_and_meaning(
                self._truncate_for_reflection(conversation_text)
            )
        else:
            result["conversation_review"] = {"emotions": "", "situation": "", "meaning": ""}

        return result

    def review_conversation_emotions_and_meaning(self, conversation_text):
        """
        Review the conversation and reflect on emotions felt, the situation, and what it could mean.
        Returns {"emotions": str, "situation": str, "meaning": str}. Empty strings on skip or failure.
        """
        empty = {"emotions": "", "situation": "", "meaning": ""}
        if not conversation_text or len(conversation_text.strip()) < 10:
            return empty
        prompt = (
            "Review the following conversation and answer in three short sections. "
            "Use exactly these labels, one per section:\n\n"
            "EMOTIONS:\n<emotions that were felt by participants or evident in the exchange>\n\n"
            "SITUATION:\n<what was going on, context>\n\n"
            "MEANING:\n<deeper meaning, implications, or subtext—what could it have meant?>\n\n"
            "Conversation:\n\n" + conversation_text
        )
        try:
            resp = self.ollama_client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            return empty
        raw = self._extract_message_content(resp)
        if not raw:
            return empty
        out = {"emotions": "", "situation": "", "meaning": ""}
        section = None
        current = []

        def _normalized_header(line):
            s = line.strip().upper()
            for prefix in ("**", ""):
                if s.startswith(prefix):
                    s = s[len(prefix):].lstrip()
                    break
            s = s.rstrip("*").strip().rstrip(":").strip()
            return s

        for line in raw.split("\n"):
            line_strip = line.strip()
            head = _normalized_header(line_strip)
            if head == "EMOTIONS":
                if section and current:
                    out[section] = "\n".join(current).strip()
                section = "emotions"
                rest_upper = line_strip.lstrip("*").strip().upper()
                rest = ""
                for token in ("EMOTIONS:", "EMOTIONS"):
                    if rest_upper.startswith(token):
                        rest = line_strip.lstrip("*").strip()[len(token):].strip().lstrip(":*").strip("*").strip()
                        break
                current = [rest] if rest else []
            elif head == "SITUATION":
                if section and current:
                    out[section] = "\n".join(current).strip()
                section = "situation"
                rest_upper = line_strip.lstrip("*").strip().upper()
                rest = ""
                for token in ("SITUATION:", "SITUATION"):
                    if rest_upper.startswith(token):
                        rest = line_strip.lstrip("*").strip()[len(token):].strip().lstrip(":*").strip("*").strip()
                        break
                current = [rest] if rest else []
            elif head == "MEANING":
                if section and current:
                    out[section] = "\n".join(current).strip()
                section = "meaning"
                rest_upper = line_strip.lstrip("*").strip().upper()
                rest = ""
                for token in ("MEANING:", "MEANING"):
                    if rest_upper.startswith(token):
                        rest = line_strip.lstrip("*").strip()[len(token):].strip().lstrip(":*").strip("*").strip()
                        break
                current = [rest] if rest else []
            elif section:
                current.append(line_strip)
        if section and current:
            out[section] = "\n".join(current).strip()
        if not any(out.values()):
            out["situation"] = raw[:4000].strip()
        return out

    def _truncate_for_reflection(self, conversation_text):
        """
        Truncate long conversation so reflection fits in context and the model
        can respond with the expected format. Keeps start and end of the chat.
        """
        if not conversation_text or len(conversation_text) <= REFLECT_CONVERSATION_MAX_CHARS:
            return conversation_text
        half = REFLECT_CONVERSATION_MAX_CHARS // 2
        start = conversation_text[:half].rstrip()
        end = conversation_text[-half:].lstrip()
        return start + "\n\n... [middle of conversation omitted] ...\n\n" + end

    def _make_conversation_summary_memory(self, parsed_messages, conversation_text):
        """
        Build a short event-style memory string for the conversation.
        Uses canonical (sorted) participant order so the same conversation always yields the same string.
        Returns (content, participants) or (None, None) if too short or empty.
        participants is a list of sender names (sorted); for 1:1 the single name is also the 'person' for the entry.
        """
        senders = sorted({m.get("sender", "Unknown") for m in parsed_messages})
        senders_str = ", ".join(senders[:5])
        if len(senders) > 5:
            senders_str += f" (+{len(senders) - 5} others)"
        first_part = conversation_text.replace("\n", " ").strip()[:120]
        if len(conversation_text) > 120:
            first_part += "..."
        summary = f"Conversation with {senders_str}: {first_part}"
        if len(first_part.strip()) < 5:
            return (None, None)
        participants = senders[:5] if senders else []
        return (summary, participants)

    def _parse_message_history(self, message_history, format):
        """
        Parse message history into a list of {sender, message, timestamp} dicts.
        """
        parsed = []
        if format == "text":
            lines = [ln.strip() for ln in message_history.split("\n")]
            i = 0
            while i < len(lines):
                line = lines[i]
                if not line:
                    i += 1
                    continue
                if self._is_sender_timestamp_line(line):
                    sender = "Unknown"
                    for sep in (", [", " - ["):
                        if sep in line:
                            sender = line.split(sep)[0].strip() or "Unknown"
                            break
                    if not sender:
                        sender = "Unknown"
                    msg_parts = []
                    i += 1
                    while i < len(lines) and lines[i] and not self._is_sender_timestamp_line(lines[i]):
                        msg_parts.append(lines[i])
                        i += 1
                    message = " ".join(msg_parts).strip() if msg_parts else ""
                    if message or sender != "Unknown":
                        parsed.append({
                            "sender": sender,
                            "message": message,
                            "timestamp": time.time()
                        })
                    continue
                sender = "Unknown"
                message = line
                for sep in [":", "-", "said:", "wrote:"]:
                    if sep in line:
                        parts = line.split(sep, 1)
                        if len(parts) == 2:
                            sender = parts[0].strip()
                            message = parts[1].strip()
                            break
                parsed.append({
                    "sender": sender,
                    "message": message,
                    "timestamp": time.time()
                })
                i += 1
        elif format == "lines":
            if isinstance(message_history, str):
                message_history = [ln.strip() for ln in message_history.split("\n") if ln.strip()]
            for line in message_history:
                line = line if isinstance(line, str) else str(line)
                if ":" in line:
                    parts = line.split(":", 1)
                    parsed.append({
                        "sender": parts[0].strip(),
                        "message": parts[1].strip() if len(parts) > 1 else "",
                        "timestamp": time.time()
                    })
                else:
                    parsed.append({
                        "sender": "Unknown",
                        "message": line,
                        "timestamp": time.time()
                    })
        elif format == "structured":
            for msg in message_history:
                sender = msg.get("sender") or msg.get("from") or msg.get("author") or "Unknown"
                message = msg.get("message") or msg.get("text") or msg.get("content") or str(msg)
                timestamp = msg.get("timestamp") or msg.get("time") or time.time()
                parsed.append({
                    "sender": str(sender),
                    "message": str(message),
                    "timestamp": float(timestamp) if isinstance(timestamp, (int, float)) else time.time()
                })
        elif format == "json":
            if isinstance(message_history, str):
                try:
                    data = json.loads(message_history)
                    return self._parse_message_history(data, "structured" if isinstance(data, list) else "text")
                except json.JSONDecodeError:
                    return self._parse_message_history(message_history, "text")
            else:
                return self._parse_message_history(message_history, "structured")
        return parsed

    def _detect_message_format(self, message_history):
        """Detect the format of message_history."""
        if isinstance(message_history, str):
            try:
                parsed = json.loads(message_history)
                return "structured" if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) else "json"
            except (json.JSONDecodeError, TypeError):
                pass
            lines = [ln.strip() for ln in message_history.split("\n") if ln.strip()]
            if not lines:
                return "text"
            if self._is_sender_timestamp_line(lines[0]):
                return "text"
            if any(":" in line for line in lines[:10]):
                return "lines"
            return "text"
        elif isinstance(message_history, list):
            if not message_history:
                return "text"
            first = message_history[0]
            if isinstance(first, dict):
                if "sender" in first or "from" in first or "author" in first:
                    return "structured"
                return "structured"
            elif isinstance(first, str):
                if ":" in first:
                    return "lines"
                return "text"
        return "text"

    def _is_sender_timestamp_line(self, line):
        """True if line looks like 'username, [timestamp]' (Telegram/WhatsApp export style)."""
        if "[" not in line:
            return False
        return bool(re.search(r"[,\-]\s*\[\d", line))

    def _is_filler_reflection(self, content):
        """True if reflection line is filler like 'None mentioned' / 'None specified' (don't store as memory)."""
        if not content or len(content) < 3:
            return True
        lower = content.lower().strip()
        filler_phrases = (
            "none mentioned", "none specified", "none added", "nothing to add",
            "no preference", "no habit", "n/a", "not specified", "not mentioned",
            "none.", "nothing.", "no facts", "no events",
        )
        return any(lower == p or lower.startswith(p + " ") or lower.startswith(p + ".") for p in filler_phrases)

    def _format_conversation_for_reflection(self, parsed_messages):
        """Format parsed messages into a conversation summary for reflection."""
        if not parsed_messages:
            return ""
        lines = []
        for msg in parsed_messages:
            sender = msg.get("sender", "Unknown")
            message = msg.get("message", "")
            lines.append(f"{sender}: {message}")
        return "\n".join(lines)

    ####################################################################
    # === Chat/Interaction/Prompt Suggestion ===
    ####################################################################

    def generate_response(
        self, prompt, include_memory=True, include_recent_thoughts=True, memory_limit=20, thoughts_limit=10
    ):
        """
        Generate a response. Optionally inject memory and recent thoughts into the prompt.
        """
        messages = []
        if include_memory or include_recent_thoughts:
            parts = []
            if include_memory:
                parts.append(self._build_memory_context(limit=memory_limit))
            if include_recent_thoughts:
                parts.append(self._build_thoughts_context(limit=thoughts_limit))
            context = "\n\n".join(p for p in parts if p).strip()
            if context:
                messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})
        return self.ollama_client.chat(model=self.model, messages=messages)

    def chat_as_personas(
        self,
        user_message,
        names,
        conversation_messages=None,
        memory_limit=35,
    ):
        """
        Simulate response(s) from one or more people using only memories that mention them.

        Args:
            user_message: The user's latest message in the role-play chat.
            names: Non-empty list of person names (as stored in memory / participants).
            conversation_messages: Optional prior turns: list of {"role": "user"|"assistant", "content": str}.
            memory_limit: Max memory entries to include (union across selected names).

        Returns:
            dict with "reply" (str), optional "error" (str). Does not inject app-user thoughts.
        """
        raw_names = [n.strip() for n in (names or []) if (n or "").strip()]
        seen = set()
        deduped = []
        for n in raw_names:
            key = n.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(n)
        if not deduped:
            return {"reply": "", "error": "Select at least one person."}
        text = (user_message or "").strip()
        if not text:
            return {"reply": "", "error": "Message is empty."}

        prior = list(conversation_messages or [])

        blocks = []
        for name in deduped:
            try:
                raw_chunk = self._chat_one_persona_voice(
                    name, text, prior, memory_limit=memory_limit
                )
            except Exception as e:
                return {"reply": "", "error": f"Model error: {e}"}
            blocks.append(self._sanitize_ai_block(name, raw_chunk))

        rp = "\n\n".join(blocks).strip()
        return {"reply": rp}

    def _chat_one_persona_voice(self, name, user_message, conversation_messages, memory_limit=35):
        """
        One Ollama call for a single named person so small models cannot mix personas or invent games.
        """
        mem_ctx = self._build_memory_context(limit=memory_limit, person=name)
        parts = []
        if mem_ctx:
            parts.append(mem_ctx)
        else:
            parts.append(
                f"(No memories tagged for {name}; reply briefly in a plausible casual voice.)"
            )
        parts.append(
            f"You are ONLY {name} in a private text chat. You are NOT a chatbot, tutor, narrator, or game master. "
            f"Write a short reply (1–4 sentences) as {name} would type, using the memories for tone and facts. "
            "FORBIDDEN: help-desk phrases, 'how can I help', invented games/rules/scenarios, story continuations, or speaking as anyone else."
        )
        if conversation_messages:
            hist = []
            for m in conversation_messages:
                if not isinstance(m, dict):
                    continue
                role = m.get("role")
                content = (m.get("content") or "").strip()
                if role == "user" and content:
                    hist.append(f"You (the user): {content}")
                elif role == "assistant" and content:
                    hist.append(content)
            if hist:
                parts.append("Earlier in this chat:\n" + "\n\n".join(hist))
        system_content = "\n\n".join(parts)
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message.strip()},
        ]
        resp = self.ollama_client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": 0.65, "num_predict": 400},
        )
        return self._extract_message_content(resp) or ""

    def _sanitize_ai_block(self, name, raw):
        """Prefix with AI (Name): and strip trailing junk (rules, games) some models append."""
        raw = (raw or "").strip()
        p = f"AI ({name}):"
        if raw.startswith(p):
            body = raw[len(p):].strip()
        else:
            body = raw
        for marker in (
            "\n\nRules:",
            "\nRules:",
            "\n\n---",
            "\n\nStory:",
            "\n\nScenario:",
            "\n\nIn this game",
            "\n\nNote:",
        ):
            if marker in body:
                body = body.split(marker)[0].strip()
        body = body.split("\n\n")[0].strip()
        if len(body) > 900:
            body = body[:900].rsplit(" ", 1)[0] + "…"
        return f"{p} {body}".strip()

    def chat_learned_self(
        self,
        user_message,
        persona_display_name,
        conversation_messages=None,
        memory_limit=35,
        thoughts_limit=8,
    ):
        """
        Conversational Q&A or drafting as the owner of the memory store (learned texting style / life context).
        Uses full memory + thoughts, not third-party persona simulation.
        """
        text = (user_message or "").strip()
        if not text:
            return {"reply": "", "error": "Message is empty."}
        name = (persona_display_name or "You").strip()
        parts = []
        mem_ctx = self._build_memory_context(limit=memory_limit)
        if mem_ctx:
            parts.append(mem_ctx)
        thoughts_ctx = self._build_thoughts_context(limit=thoughts_limit)
        if thoughts_ctx:
            parts.append(thoughts_ctx)
        parts.append(
            f"You are answering for {name} (the human who owns this memory store), not as a generic chatbot. "
            "Use memories to match their voice, relationships, slang, emoji habits, and typical reactions. "
            "Write in first person as they would naturally chat—short unless they asked for detail. "
            "Do not open with help-desk phrases unless their VOICE memories justify it."
        )
        system_content = "\n\n".join(parts)
        messages = [{"role": "system", "content": system_content}]
        prior = list(conversation_messages or [])
        for m in prior:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            content = (m.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": text})
        try:
            resp = self.ollama_client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.65, "num_predict": 700},
            )
        except Exception as e:
            return {"reply": "", "error": f"Model error: {e}"}
        reply = self._extract_message_content(resp) or ""
        return {"reply": reply.strip()}

    def suggest_reply(
        self,
        chat_history,
        user_prompt=None,
        format="auto",
        memory_limit=20,
        thoughts_limit=10,
    ):
        """
        Ask the brain how to reply based on chat history. Uses memory and recent
        thoughts so suggestions are consistent with what the brain knows about the user.

        Args:
            chat_history: Same as teach_from_message_history (string, list of dicts,
                list of "sender: message" strings, or JSON string).
            user_prompt: Question to ask, e.g. "How should I reply?" or "Suggest a
                professional reply." If None, uses a default prompt.
            format: "auto", "text", "structured", "lines", "json"
            memory_limit: Max memories to include in context.
            thoughts_limit: Max thoughts to include in context.

        Returns:
            dict with:
                - "reply": suggested reply text (model output)
                - "conversation_preview": first N chars of conversation used
        """

        default_prompt = (
            "Based on the conversation above and the information you have about the user (me), "
            "suggest a short reply that I (the user) could send. Reply with only the suggested message, no extra explanation."
        )
        prompt = (user_prompt or default_prompt).strip() or default_prompt

        if format == "auto":
            format = self._detect_message_format(chat_history)
        parsed = self._parse_message_history(chat_history, format)
        if not parsed:
            return {"reply": "", "conversation_preview": "", "error": "No messages in chat history"}

        conversation_text = self._format_conversation_for_reflection(parsed)
        conversation_preview = conversation_text[:500] + ("..." if len(conversation_text) > 500 else "")

        # Use consider_what_to_say for additional reasoning and context
        reasoning_result = self.consider_what_to_say(
            conversation_text,
            memory_limit=memory_limit,
            thoughts_limit=thoughts_limit,
        )

        parts = []
        mem_ctx = self._build_memory_context(limit=memory_limit)
        if mem_ctx:
            parts.append(mem_ctx)
        thoughts_ctx = self._build_thoughts_context(limit=thoughts_limit)
        if thoughts_ctx:
            parts.append(thoughts_ctx)
        parts.append("Conversation so far:\n" + conversation_text)
        parts.append(
            "Reply style: Prefer the user's real texting voice when inferable (especially VOICE, TOPIC_STYLE, "
            "REACTION, HABIT, and chat-derived memories). Suggest a line they could paste into a messenger "
            "(e.g. Telegram)—casual length and tone—unless the thread clearly requires formality."
        )

        # Include the model's reasoning to boost reply suggestion quality, if available
        if reasoning_result and ("to_say" in reasoning_result or "not_to_say" in reasoning_result):
            to_say = reasoning_result.get("to_say", "")
            not_to_say = reasoning_result.get("not_to_say", "")
            if to_say:
                parts.append("Reasoned possible reply:\n" + to_say)
            if not_to_say:
                parts.append("What to avoid saying:\n" + not_to_say)

        system_content = "\n\n".join(parts)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]
        try:
            resp = self.ollama_client.chat(model=self.model, messages=messages)
        except Exception as e:
            return {
                "reply": "",
                "conversation_preview": conversation_preview,
                "error": f"Model error: {e}",
            }

        suggestion = self._extract_message_content(resp) or ""
        return {
            "reply": suggestion.strip(),
            "conversation_preview": conversation_preview,
            "reasoning": reasoning_result,
        }

    def classify_reply_tone(self, reply):
        """
        Classify a reply as logical vs emotional. Returns a score (0 = logical, 1 = emotional)
        and a label: "logical", "emotional", or "balanced".

        Args:
            reply: The reply text to classify.

        Returns:
            dict with "score" (float 0–1), "label" ("logical"|"emotional"|"balanced"), and optionally "error".
        """
        if not (reply or "").strip():
            return {"score": 0.5, "label": "balanced", "error": "Empty reply"}
        prompt = (
            "Rate how logical vs emotional this message is. "
            "Reply with ONLY a single number from 0 to 1: 0 = purely logical/neutral, 1 = purely emotional. "
            "E.g. 0.2 for mostly logical, 0.8 for mostly emotional, 0.5 for balanced.\n\nMessage:\n"
            + (reply or "").strip()
        )
        try:
            resp = self.ollama_client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            text = self._extract_message_content(resp) or ""
            # Try to extract a number 0–1
            match = re.search(r"0?\.\d+|1\.0?|[01]", text.strip())
            if match:
                score = float(match.group())
                if score > 1:
                    score = 1.0
                elif score < 0:
                    score = 0.0
            else:
                score = 0.5
            if score < 0.35:
                label = "logical"
            elif score > 0.65:
                label = "emotional"
            else:
                label = "balanced"
            return {"score": score, "label": label}
        except Exception as e:
            return {"score": 0.5, "label": "balanced", "error": str(e)}

    def adjust_reply_tone(
        self,
        reply,
        chat_history=None,
        direction="more_logical",
        memory_limit=10,
        thoughts_limit=5,
    ):
        """
        Rewrite a reply to be more logical or more emotional while keeping the same meaning and context.

        Args:
            reply: Current reply text.
            chat_history: Optional conversation context (same formats as suggest_reply).
            direction: "more_logical" or "more_emotional".
            memory_limit: Max memories for context.
            thoughts_limit: Max thoughts for context.

        Returns:
            dict with "reply" (rewritten text) and optionally "error".
        """
        if not (reply or "").strip():
            return {"reply": "", "error": "Empty reply"}
        if direction not in ("more_logical", "more_emotional"):
            direction = "more_logical"
        instruction = (
            "Rewrite the following reply to be more logical and factual: keep the same meaning but use neutral, "
            "clear language and avoid emotional or subjective wording."
            if direction == "more_logical"
            else "Rewrite the following reply to be more warm and emotional: keep the same meaning but add empathy, "
            "warmth, or personal feeling where appropriate."
        )
        parts = []
        mem_ctx = self._build_memory_context(limit=memory_limit)
        if mem_ctx:
            parts.append(mem_ctx)
        thoughts_ctx = self._build_thoughts_context(limit=thoughts_limit)
        if thoughts_ctx:
            parts.append(thoughts_ctx)
        if chat_history:
            parsed = self._parse_message_history(chat_history, self._detect_message_format(chat_history))
            if parsed:
                conv_text = self._format_conversation_for_reflection(parsed)
                parts.append("Conversation context:\n" + conv_text)
        parts.append("Current reply to rewrite:\n" + (reply or "").strip())
        parts.append("Instruction: " + instruction + " Reply with ONLY the rewritten message, no explanation.")
        system_content = "\n\n".join(parts)
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "Output only the rewritten reply, nothing else."},
        ]
        try:
            resp = self.ollama_client.chat(model=self.model, messages=messages)
            new_reply = self._extract_message_content(resp) or ""
            return {"reply": new_reply.strip() or reply.strip()}
        except Exception as e:
            return {"reply": reply.strip(), "error": str(e)}

    def suggest_actions_for_situation(
        self,
        situation_description,
        memory_limit=20,
        thoughts_limit=10,
        persona_name=None,
    ):
        """
        Given a situation description, suggest the top 5 actions the person would
        most likely take based on memory and recent thoughts.

        Args:
            situation_description: User's description of the situation.
            memory_limit: Max memories to include in context.
            thoughts_limit: Max thoughts to include in context.
            persona_name: Optional name to use in the prompt (e.g. "What would [Name] do?").

        Returns:
            dict with "actions" (list of up to 5 strings) and "raw" (full model text).
        """
        parts = []
        mem_ctx = self._build_memory_context(limit=memory_limit)
        if mem_ctx:
            parts.append(mem_ctx)
        thoughts_ctx = self._build_thoughts_context(limit=thoughts_limit)
        if thoughts_ctx:
            parts.append(thoughts_ctx)
        parts.append(
            "When inferring what they would do, lean on their stored preferences, habits, beliefs, "
            "relationship norms, and reaction-style memories when those apply to the situation."
        )
        system_content = "\n\n".join(parts) if parts else ""
        who = persona_name if persona_name else "I"
        user_prompt = (
            f"Based only on the memory and history above, what are the top 5 actions that {who} "
            f"would most likely take in the following situation? Please be clear and specific in referring to '{who}' in each suggested action. "
            "Reply with exactly 5 actions, numbered 1. through 5., one per line. Be concise and refer explicitly to who is acting in each case.\n\n"
            "Situation:\n" + (situation_description or "").strip()
        )
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": user_prompt})
        try:
            resp = self.ollama_client.chat(model=self.model, messages=messages)
        except Exception as e:
            return {"actions": [], "raw": "", "error": str(e)}
        raw = self._extract_message_content(resp) or ""
        actions = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Match lines like "1. ..." or "1) ..."
            if re.match(r"^[1-5][.)]\s*", line):
                action = re.sub(r"^[1-5][.)]\s*", "", line).strip()
                if action:
                    actions.append(action)
        if not actions and raw:
            actions = [raw]
        return {"actions": actions[:5], "raw": raw}

    ####################################################################
    # === Chat Response Extraction Utility ===
    ####################################################################

    def _extract_message_content(self, resp):
        """
        Extract assistant message content from ollama chat response.
        Handles both dict and object-style responses from the ollama client.
        """
        if resp is None:
            return ""
        if isinstance(resp, dict):
            msg = resp.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                return (content or "").strip()
            return ""
        try:
            msg = getattr(resp, "message", None)
            if msg is not None:
                content = getattr(msg, "content", None)
                if content is not None:
                    return (content if isinstance(content, str) else str(content)).strip()
        except (AttributeError, TypeError):
            pass
        return ""