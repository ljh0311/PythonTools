"""
Training helpers: ATC text hygiene (all modes) + situational labels.

- **Pilot trainee** (`MainWindow`, role=pilot): use `build_pilot_situation_line` /
  `infer_phase_from_atc` / `infer_phase_from_pilot` for first-person cues.
- **ATC trainee** (`ATCWindow`, role=atc): use `build_atc_traffic_strip_line` /
  `traffic_instruction_category` — third-person / traffic-only, not "your" phase.

Clearance repair + dedupe helpers are shared wherever AI emits ATC phraseology.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# --- Clearance repair (takeoff vs taxi conflicts) ---

_TAKEOFFISH = re.compile(
    r"\b(cleared\s+for\s+takeoff|cleared\s+to\s+take\s*off|"
    r"line\s+up\s+and\s+wait|position\s+and\s+hold)\b",
    re.I,
)
_WHEN_READY_TAXI = re.compile(
    r",?\s*contact\s+[^.]+?\s+when\s+ready\s+to\s+taxi\.?",
    re.I,
)
_STANDALONE_READY_TAXI = re.compile(r",?\s*when\s+ready\s+to\s+taxi\.?", re.I)


def repair_conflicting_clearance(text: str) -> Tuple[str, List[str]]:
    """
    Remove impossible combinations of takeoff/line-up phraseology with taxi-only
    clauses (common LLM failure mode).
    """
    notes: List[str] = []
    if not text or not text.strip():
        return text, notes

    original = text.strip()
    fixed = original

    if _TAKEOFFISH.search(fixed) and _WHEN_READY_TAXI.search(fixed):
        fixed = _WHEN_READY_TAXI.sub("", fixed)
        notes.append("removed_contact_when_ready_to_taxi_under_takeoff_clearance")

    if _TAKEOFFISH.search(fixed) and _STANDALONE_READY_TAXI.search(fixed):
        fixed = _STANDALONE_READY_TAXI.sub("", fixed)
        notes.append("removed_when_ready_to_taxi_under_takeoff_clearance")

    # Takeoff clearance + explicit taxi-to-runway in one transmission (incoherent)
    if re.search(r"\bcleared\s+for\s+takeoff\b", fixed, re.I) and re.search(
        r"\btaxi\s+to\s+runway\b", fixed, re.I
    ):
        fixed = re.sub(
            r",?\s*taxi\s+to\s+runway\s+[^,.]+(\s+via[^,.]+)?",
            "",
            fixed,
            flags=re.I,
        )
        notes.append("removed_taxi_to_runway_under_takeoff_clearance")

    fixed = re.sub(r"\s{2,}", " ", fixed).strip(" ,")
    if fixed and not fixed.endswith("."):
        fixed += "."
    return fixed, notes


def normalize_for_dedupe(text: str) -> str:
    """Normalize for comparing two ATC lines."""
    if not text:
        return ""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


_READBACK_REQUIRED_CUES = re.compile(
    r"\b(cleared\s+for\s+takeoff|cleared\s+for\s+landing|cleared\s+to\s+land|cleared\s+via|cleared\s+to\s+taxi|"
    r"line\s+up\s+and\s+wait|position\s+and\s+hold|hold\s+short|taxi\s+(to|via)|"
    r"cross\s+runway|pushback\s+approved|squawk\s+\d|climb\s+and\s+maintain|"
    r"descend\s+and\s+maintain)\b",
    re.I,
)


def clearance_requires_readback(atc_text: str) -> bool:
    """True when the given ATC line is the kind of instruction that normally needs a pilot readback."""
    if not atc_text or len(atc_text.strip()) < 12:
        return False
    return bool(_READBACK_REQUIRED_CUES.search(atc_text))


def pilot_ack_only(pilot_message: str) -> bool:
    """
    True if the pilot only acknowledges without repeating clearance elements
    (e.g. single-word 'Roger' after a clearance).
    """
    if not pilot_message or not pilot_message.strip():
        return False
    if pilot_message_sounds_like_readback(pilot_message):
        return False
    m = pilot_message.strip().lower()
    if len(m) > 88:
        return False
    if re.search(
        r"\b(cleared|runway|rwys?|sid|star|taxi|maintain|heading|departure|approach|"
        r"contact\s+\w|squawk|\d{3}\.\d+)\b",
        m,
    ):
        return False
    if re.match(
        r"^[\s,.'-]*(roger|wilco|affirmative|copy|thanks?|thank\s+you|standing\s+by|"
        r"good\s+day|hello|ok|okay)+[\s,.'-]*$",
        m,
    ):
        return True
    words = re.findall(r"[a-zA-Z]+", pilot_message)
    return len(words) <= 5 and any(
        w.lower() in ("roger", "wilco", "copy", "affirmative") for w in words
    )


def pilot_answered_information_request_about_altitude(pilot_message: str) -> bool:
    """
    True if the pilot likely answered an altitude / level check (not silence or unrelated).
    Used to break AI loops that repeat the same question after the pilot already responded.
    """
    pl = (pilot_message or "").strip()
    if not pl:
        return False
    low = pl.lower()
    if re.search(r"\b(?:fl|flight\s*level)\s*\d{2,3}\b", low, re.I):
        return True
    if re.search(r"\bf\s*\d{2,3}\b", low, re.I):
        return True
    if re.search(r"\b\d{3,4}\s*(?:feet|ft)\b", low):
        return True
    if re.search(r"\b(currently\s+at|level\s+at|maintain(?:ing)?)\b", low) and re.search(
        r"\d{2,4}", low
    ):
        return True
    if len(low) > 120:
        return False
    if re.search(r"\b(affirmative|confirm(?:ed)?|correct)\b", low):
        return True
    if re.fullmatch(r"yes[\s?!.'-]*", low) or re.fullmatch(r"yeah[\s?!.'-]*", low):
        return True
    if re.fullmatch(r"roger[\s?!.'-]*", low):
        return True
    return False


def pilot_requests_descend_maintain_fl(pilot_message: str) -> Optional[str]:
    """Extract requested flight level after descend/decend (handles 'at FL300 ... descend to FL280')."""
    low = (pilot_message or "").lower()
    idx = low.find("descend")
    if idx < 0:
        idx = low.find("decend")
    if idx < 0:
        return None
    tail = low[idx:]
    m = re.search(r"(?:fl|flight\s*level|f)\s*(\d{2,3})\b", tail, re.I)
    return m.group(1) if m else None


def pilot_requests_climb_maintain_fl(pilot_message: str) -> Optional[str]:
    low = (pilot_message or "").lower()
    idx = low.find("climb")
    if idx < 0:
        return None
    tail = low[idx:]
    m = re.search(r"(?:fl|flight\s*level|f)\s*(\d{2,3})\b", tail, re.I)
    return m.group(1) if m else None


def pilot_indicates_frequency_change_compliance(pilot_message: str) -> bool:
    """Pilot states or role-plays switching frequency after a 'contact ... on' handoff."""
    raw = pilot_message or ""
    low = raw.lower()
    if "*" in raw and re.search(r"(switch|switching|contact|tuned)", low):
        return True
    if re.search(r"\b(?:switching|switched)\s+(?:to\s+)?(?:frequency\s+)?\d", low):
        return True
    if re.search(
        r"\bcontacting\s+(?:departure|approach|tower|ground|center|delivery)\s+on\s+\d",
        low,
    ):
        return True
    if "tuned" in low and re.search(r"\d{3}\.\d{1,3}", raw):
        return True
    return False


def pilot_sector_initial_checkin(pilot_message: str) -> Optional[str]:
    """
    If the pilot addresses an ATC unit by name (e.g. 'Departure, Singapore 123, with you'),
    return that unit in lowercase. Otherwise None.
    """
    low = (pilot_message or "").strip().lower()
    m = re.match(
        r"^(departure|approach|tower|ground|delivery|center|radar)\b",
        low,
    )
    if not m:
        return None
    unit = m.group(1)
    if unit in ("departure", "approach", "center", "radar"):
        if re.search(
            r"\b(with you|checking in|established|passing|leaving|"
            r"good morning|good day|good evening)\b",
            low,
        ):
            return unit
        if len(low) <= 58 and low.count(",") >= 1:
            return unit
        return None
    if unit in ("tower", "ground", "delivery"):
        if any(
            c in low
            for c in (
                "with you",
                "holding",
                "ready",
                "checking in",
                "at gate",
                "inbound",
            )
        ):
            return unit
    return None


def atc_prompt_hint_from_pilot_transmission(pilot_message: str) -> str:
    """Injected into the LLM context for realistic handoffs and sector changes."""
    if pilot_indicates_frequency_change_compliance(pilot_message):
        return (
            "TRANSMISSION CONTEXT (handoff compliance): The pilot is acknowledging or simulating "
            "the frequency change after you issued 'contact [facility] on [frequency]'. "
            "Reply briefly as the handing-off sector (e.g. 'Wilco' or 'Roger, good day'). "
            "Do NOT repeat the frequency; do NOT issue departure/approach radar instructions here "
            "— those belong to the next sector after they check in on that frequency."
        )
    unit = pilot_sector_initial_checkin(pilot_message)
    if unit in ("departure", "approach", "center", "radar"):
        return (
            f"TRANSMISSION CONTEXT (new frequency / {unit}): The pilot is checking in with "
            f"{unit.upper()} (initial call on this frequency). Respond AS {unit.upper()} radar "
            "control, not as tower on a ground frequency. Use sector-appropriate phraseology: "
            "radar contact or identified; acknowledge passing level if stated; continue climb "
            "via SID, assigned heading, traffic, or flight level from the scenario — not a generic "
            "'maintain current altitude and heading until further cleared' unless it matches a "
            "known assigned mode from the history."
        )
    if unit in ("tower", "ground", "delivery"):
        return (
            f"TRANSMISSION CONTEXT: The pilot is addressing {unit.upper()}. Reply as that unit "
            "with appropriate surface / tower phraseology."
        )
    return ""


def readback_training_reminder_line(callsign: str) -> str:
    """Deterministic ATC reply for pilot training when a readback was required but missing."""
    return (
        f"{callsign}, negative, that is not an acceptable readback. "
        f"When ATC issues a clearance you must read back the safety-related items "
        f"(for example cleared route or SID, runway if given, and assigned frequency). "
        f"A single acknowledgment such as \"Roger\" alone is not sufficient. "
        f"Say again with your full readback."
    )


def pilot_message_sounds_like_readback(pilot_message: str) -> bool:
    m = pilot_message.lower()
    if len(m) < 12:
        return False
    runwayish = bool(re.search(r"\b(runway|rwy)\s*\d", m)) or bool(re.search(r"\b\d{2}[lrc]?\b", m))
    ack = any(
        k in m
        for k in (
            "cleared",
            "wilco",
            "read back",
            "readback",
            "copy",
            "understood",
            "contact departure",
            "contact tower",
            "contact ground",
        )
    )
    return runwayish and ack


def traffic_instruction_category(atc_text: str) -> str:
    """Neutral summary of an ATC/GROUND line for **ATC trainee** traffic context."""
    t = atc_text.lower()
    if re.search(r"\bcleared\s+for\s+takeoff\b", t):
        return "Takeoff clearance (traffic should be aligned / rolling)"
    if "line up and wait" in t or "position and hold" in t:
        return "Line up and wait (traffic on runway, not takeoff-cleared)"
    if re.search(r"\bcleared\s+to\s+land\b", t):
        return "Landing clearance"
    if "hold short" in t:
        return "Hold short / protected area"
    if re.search(r"\btaxi\s+", t) or "pushback" in t:
        return "Taxi / pushback / surface"
    if re.search(r"\bcontact\s+", t):
        return "Frequency / handoff"
    if "standby" in t:
        return "Stand by"
    if "roger" in t or "wilco" in t:
        return "Acknowledgment"
    return "Other / general"


def infer_phase_from_atc(atc_text: str) -> str:
    """First-person phase hint for **pilot trainee** UI only."""
    t = atc_text.lower()
    if re.search(r"\bcleared\s+for\s+takeoff\b", t):
        return "Cleared for takeoff (you should be lined up or rolling)"
    if "line up and wait" in t or "position and hold" in t:
        return "Line up and wait (on runway, not cleared for takeoff yet)"
    if re.search(r"\bcleared\s+to\s+land\b", t):
        return "Landing clearance"
    if "hold short" in t:
        return "Hold short of runway / protected area"
    if re.search(r"\btaxi\s+", t) or "pushback" in t:
        return "Surface movement (taxi / pushback)"
    if re.search(r"\bcontact\s+", t):
        return "Frequency change / handoff"
    if "standby" in t:
        return "Stand by (await ATC)"
    if "roger" in t or "wilco" in t:
        return "Acknowledgment"
    return "Listen for further instruction"


def infer_phase_from_pilot(pilot_text: str) -> Optional[str]:
    m = pilot_text.lower()
    if "holding short" in m or "hold short" in m:
        return "You reported: holding short"
    if "ready for departure" in m or "request takeoff" in m or "ready for takeoff" in m:
        return "You reported: ready for departure / takeoff"
    if "request taxi" in m or "ready to taxi" in m:
        return "You reported: taxi intent"
    if "cleared" in m and "takeoff" in m:
        return "You read back: takeoff"
    if "cleared" in m and "land" in m:
        return "You read back: landing"
    return None


def build_atc_traffic_strip_line(
    callsign: str,
    location: str,
    status: str,
    last_atc_or_ground_to_callsign: str,
    last_pilot_line_in_log: str,
    max_pilot_snip: int = 72,
) -> str:
    """
    One line for **ATC trainee** Ground tab: selected traffic + list state + comms context.
    Does not imply the trainee is the pilot.
    """
    loc = (location or "").strip() or "—"
    st = (status or "").strip() or "—"
    if last_atc_or_ground_to_callsign.strip():
        cat = traffic_instruction_category(last_atc_or_ground_to_callsign)
        last_part = f"Last ATC/GROUND to them: {cat}"
    else:
        last_part = "No ATC/GROUND line to this callsign in this log yet"
    line = f"Selected traffic: {callsign}  |  List: {loc}  |  Status: {st}  |  {last_part}"
    pl = (last_pilot_line_in_log or "").strip()
    if pl:
        snip = pl if len(pl) <= max_pilot_snip else pl[: max_pilot_snip - 1] + "…"
        line += f"  |  Last pilot line in log (simulated / practice): {snip}"
    return line


def build_pilot_situation_line(
    callsign: str,
    location: str,
    status: str,
    last_atc_snippet: str,
    pilot_hint: Optional[str],
) -> Tuple[str, str]:
    """
    **Pilot trainee** (`MainWindow`): first-person phase + list row.

    Returns (one_line_summary, detail_for_tooltip_or_secondary).
    """
    loc = (location or "").strip() or "—"
    st = (status or "").strip() or "—"
    atc_phase = infer_phase_from_atc(last_atc_snippet) if last_atc_snippet else "No recent ATC to you"
    pilot_phase = pilot_hint or ""
    detail_parts = [f"Callsign: {callsign}", f"List: {loc}", f"Status: {st}", f"ATC phase: {atc_phase}"]
    if pilot_phase:
        detail_parts.append(pilot_phase)
    summary = f"{callsign}  |  {loc}  |  {st}  |  Phase: {atc_phase}"
    return summary, " · ".join(detail_parts)


# Back-compat alias (pilot strip)
def build_trainee_status_line(
    callsign: str,
    location: str,
    status: str,
    last_atc_snippet: str,
    pilot_hint: Optional[str],
) -> Tuple[str, str]:
    return build_pilot_situation_line(callsign, location, status, last_atc_snippet, pilot_hint)
