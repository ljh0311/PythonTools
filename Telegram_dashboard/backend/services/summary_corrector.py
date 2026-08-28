import re
import logging
from difflib import SequenceMatcher
from typing import Any

# Log name corrections for debugging
logger = logging.getLogger("summary_corrector")

# Matches words that look like usernames: @handle or CamelCase/under_score words
# We exclude very common short words from being candidates for correction unless they have an @
_NAME_TOKEN = re.compile(r"@?[A-Za-z][A-Za-z0-9_]{1,31}\b")
_ALIAS_SPLIT = re.compile(r"[/,;|\s]+")

_STOP_WORDS = frozenset(
    {
        "the", "and", "for", "are", "this", "that", "with", "from", "they", "will",
        "about", "would", "there", "their", "what", "which", "when", "where", "who",
        "how", "your", "them", "then", "than", "some", "other", "into", "just",
        "been", "could", "should", "only", "well", "very", "also", "even", "back",
        "after", "over", "under", "again", "more", "most", "each", "both", "last",
        "next", "much", "many", "such", "said", "came", "went", "made", "used",
        "work", "call", "name", "good", "best", "once", "here", "look",
        "take", "than", "seen", "chat", "summary", "user", "contact",
        "alias", "person", "group", "operator", "dashboard", "message", "reply",
        "was", "were", "has", "have", "had", "not", "but", "all", "any", "can",
        "out", "one", "use", "now", "our", "him", "her", "his", "has", "its",
        "she", "you", "me", "my", "we", "us", "if", "or", "as", "at", "by", "an", "be", "so", "up"
    }
)


def _normalize_name(name: str) -> str:
    return name.lstrip("@").lower()


def _is_stop_word(name: str) -> bool:
    if name.startswith("@"):
        return False
    return name.lower() in _STOP_WORDS


def _display_name(canonical: str, matched: str) -> str:
    body = canonical.lstrip("@")
    if matched.startswith("@"):
        return f"@{body}"
    # Preserve capitalization if the original was capitalized
    if matched[:1].isupper() and body[:1].islower():
        return body[:1].upper() + body[1:]
    return body


def _usernames_from_messages(messages: list[dict[str, Any]]) -> dict[str, str]:
    known: dict[str, str] = {}
    for msg in messages:
        username = (msg.get("username") or "").strip()
        if not username:
            continue
        key = _normalize_name(username)
        if key not in known:
            known[key] = username
    return known


def _add_alias(rules: dict[str, str], alias: str, canonical_key: str) -> None:
    # Never map a stop word as an alias unless it's an @mention
    if _is_stop_word(alias) and not alias.startswith("@"):
        return
    alias_key = _normalize_name(alias)
    # Never map a stop word as a canonical target either
    if _is_stop_word(canonical_key):
        return

    if alias_key and alias_key != canonical_key:
        # Avoid circular or contradictory rules
        if alias_key not in rules:
            rules[alias_key] = canonical_key


def parse_alias_rules(*texts: str) -> dict[str, str]:
    """Map alias (lowercase) -> canonical username key (lowercase)."""
    rules: dict[str, str] = {}
    blob = "\n".join(t for t in texts if t and t.strip())
    if not blob.strip():
        return rules

    # 1. Look for explicit patterns like "X is the same as Y"
    _ALIAS_PATTERNS = [
        re.compile(
            r"(?P<canonical>@?\w+)\s*(?:is|=|:)\s*(?:the\s+same\s+(?:person|user|account)\s+as\s+)?(?P<aliases>[\w@/.,\s-]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<wrong>@?\w+)\s+(?:is\s+)?(?:wrong|incorrect|typo)\s*,?\s*(?:correct(?:\s+name)?\s+is\s+)(?P<canonical>@?\w+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"correct\s+name\s+is\s+(?P<canonical>@?\w+)(?:\s*,?\s*(?:not|instead\s+of)\s+(?P<wrong>@?\w+))?",
            re.IGNORECASE,
        ),
    ]

    for pattern in _ALIAS_PATTERNS:
        for match in pattern.finditer(blob):
            canonical = match.group("canonical")
            canonical_key = _normalize_name(canonical)
            if not canonical_key or (_is_stop_word(canonical) and not canonical.startswith("@")):
                continue

            aliases = match.groupdict().get("aliases")
            wrong = match.groupdict().get("wrong")
            if aliases:
                # If aliases is a long sentence, it's probably not a list of aliases
                pieces = _ALIAS_SPLIT.split(aliases)
                if len(pieces) > 5:
                    continue
                for alias in pieces:
                    cleaned = alias.strip().strip(".")
                    if cleaned:
                        _add_alias(rules, cleaned, canonical_key)
            if wrong:
                _add_alias(rules, wrong, canonical_key)

    # 2. Look for simple "=" or ":" lines, but only if they look like name assignments
    for line in blob.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        left, right = line.split("=", 1)
        left = left.strip()
        right = right.strip()
        
        # Heuristic: assignments like "we = the group" are sentences, not alias rules.
        # Real aliases usually have 1 word on the left and 1-3 words on the right.
        if " " in left and not left.startswith("@"):
            continue
        
        left_key = _normalize_name(left)
        if not left_key or (_is_stop_word(left) and not left.startswith("@")):
            continue

        right_pieces = _ALIAS_SPLIT.split(right)
        if len(right_pieces) > 3:
            continue # Likely a sentence

        for piece in right_pieces:
            alias = piece.strip().strip(".")
            if not alias or (_is_stop_word(alias) and not alias.startswith("@")):
                continue
            alias_key = _normalize_name(alias)
            if left_key and alias_key and left_key != alias_key:
                _add_alias(rules, alias_key, left_key)

    return rules


def _find_fuzzy_canonical(token: str, known: dict[str, str]) -> str | None:
    # Never fuzzy match common words
    if _is_stop_word(token) or len(token) < 3:
        return None

    key = _normalize_name(token)
    if key in known:
        return known[key]

    best_key: str | None = None
    best_score = 0.0
    for candidate_key in known:
        # Distance calculation
        score = SequenceMatcher(None, key, candidate_key).ratio()
        
        # Stricter requirements for fuzzy matching
        # 1. Must be high similarity
        # 2. Short words (<= 4 chars) must be extremely similar (90%+)
        # 3. Must not be a stop word
        min_score = 0.92 if len(key) <= 5 else 0.85
        
        if score > best_score and score >= min_score:
            best_key = candidate_key
            best_score = score

    if best_key is None:
        return None
    return known[best_key]


def _chat_titles_from_messages(messages: list[dict[str, Any]]) -> set[str]:
    titles: set[str] = set()
    for msg in messages:
        title = (msg.get("chat_title") or "").strip()
        if title:
            titles.add(title.lower())
    return titles


def align_summary_with_context(
    summary: str,
    messages: list[dict[str, Any]],
    *,
    ai_context: str = "",
    relationship: str = "",
    fuzzy: bool = True,
) -> tuple[str, list[dict[str, str]]]:
    """
    Fix names in an AI summary using message usernames and operator context.
    Returns (corrected_summary, corrections_applied).
    """
    if not summary or not summary.strip():
        return summary, []

    known = _usernames_from_messages(messages)
    protected_titles = _chat_titles_from_messages(messages)
    alias_rules = parse_alias_rules(ai_context, relationship)

    # Populate known with explicit aliases from context if the target exists in messages
    # or if the target itself looks like a proper name.
    for alias_key, canonical_key in alias_rules.items():
        if canonical_key in known:
            known.setdefault(alias_key, known[canonical_key])
        elif not _is_stop_word(canonical_key):
            # Target is a new name from context
            known.setdefault(canonical_key, canonical_key)
            known.setdefault(alias_key, canonical_key)

    corrections: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        
        # Basic sanity checks: 
        # - Don't correct stop words unless it was an explicit user alias
        # - Don't correct tiny words (1-2 chars) unless it's a known handle
        if _is_stop_word(token) and not token.startswith("@"):
            key = _normalize_name(token)
            if key not in alias_rules:
                return token
        
        key = _normalize_name(token)

        # Never rewrite group/channel titles (e.g. "Disparate" from "We are disparate")
        if key in protected_titles or any(
            key in title.split() for title in protected_titles if " " in title
        ):
            return token

        target_display: str | None = None
        
        # 1. Check explicit alias rules first
        if key in alias_rules:
            canonical_key = alias_rules[key]
            target_display = known.get(canonical_key, canonical_key)
        
        # 2. Check if it's a known username (possibly with different casing)
        elif key in known:
            target_display = known[key]
            
        # 3. Fuzzy matching for typos
        elif fuzzy:
            target_display = _find_fuzzy_canonical(token, known)

        if not target_display:
            return token

        corrected = _display_name(target_display, token)
        
        # Final safety check: if we are about to change a word that isn't @mention
        # to something else, make sure it's not a stop word collision.
        if corrected == token:
            return token

        # If the original token was a stop word, we ONLY replace if it was an explicit alias
        if _is_stop_word(token) and key not in alias_rules:
            return token

        pair = (token, corrected)
        if pair not in seen:
            seen.add(pair)
            corrections.append({"from": token, "to": corrected})

        return corrected

    # We process the summary word by word using the regex
    corrected_summary = _NAME_TOKEN.sub(replace_token, summary)
    return corrected_summary, corrections
