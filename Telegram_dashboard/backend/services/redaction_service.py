import os
import re
from dataclasses import dataclass

DEFAULT_PATTERNS = [
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[REDACTED_CARD]"),
    (r"\b[STFG]\d{7}[A-Z]\b", "[REDACTED_ID]"),
    (r"\b[A-Z]{1,2}\d{6,9}\b", "[REDACTED_ID]"),
    (r"\b\d{9,}\b", "[REDACTED_ID]"),
]


@dataclass
class RedactionResult:
    text: str
    redaction_count: int
    redaction_applied: bool


class RedactionService:
    def __init__(self, extra_patterns: str = ""):
        self.patterns: list[tuple[re.Pattern[str], str]] = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in DEFAULT_PATTERNS
        ]
        if extra_patterns.strip():
            for part in extra_patterns.split(","):
                part = part.strip()
                if part:
                    self.patterns.append((re.compile(part, re.IGNORECASE), "[REDACTED]"))

    def redact(self, text: str) -> RedactionResult:
        redaction_count = 0
        result = text
        for pattern, replacement in self.patterns:
            result, count = pattern.subn(replacement, result)
            redaction_count += count
        return RedactionResult(
            text=result,
            redaction_count=redaction_count,
            redaction_applied=redaction_count > 0,
        )

    def redact_messages(self, messages: list[dict]) -> tuple[list[dict], int, bool]:
        total = 0
        redacted_messages = []
        for message in messages:
            item = dict(message)
            outcome = self.redact(item.get("text", ""))
            item["text_redacted"] = outcome.text
            total += outcome.redaction_count
            redacted_messages.append(item)
        return redacted_messages, total, total > 0


extra = os.getenv("REDACTION_EXTRA_PATTERNS", "")
redaction_service = RedactionService(extra_patterns=extra)
