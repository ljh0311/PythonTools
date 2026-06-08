"""
Assessment Engine for Pilot Training
Provides real-time scoring, readback accuracy assessment, phraseology validation, and error detection
"""

import re
import time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ErrorType(Enum):
    """Types of errors in pilot communications"""
    PHRASEOLOGY_ERROR = "phraseology_error"
    READBACK_ERROR = "readback_error"
    MISSING_INFORMATION = "missing_information"
    INCORRECT_INFORMATION = "incorrect_information"
    TIMING_ERROR = "timing_error"
    PROCEDURE_ERROR = "procedure_error"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class CommunicationError:
    """Represents an error in pilot communication"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
            "timestamp": self.timestamp,
            "context": self.context
        }


@dataclass
class AssessmentResult:
    """Result of an assessment"""
    score: float  # 0-100
    errors: List[CommunicationError] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    accuracy_percentage: float = 0.0
    response_time_avg: float = 0.0
    phraseology_score: float = 0.0
    readback_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "score": self.score,
            "errors": [e.to_dict() for e in self.errors],
            "strengths": self.strengths,
            "recommendations": self.recommendations,
            "accuracy_percentage": self.accuracy_percentage,
            "response_time_avg": self.response_time_avg,
            "phraseology_score": self.phraseology_score,
            "readback_score": self.readback_score,
            "metadata": self.metadata
        }


class PhraseologyValidator:
    """Validates ATC phraseology"""
    
    # Standard ATC phraseology patterns
    PHRASEOLOGY_PATTERNS = {
        "readback_acknowledgment": [
            r"roger",
            r"wilco",
            r"affirmative",
            r"negative"
        ],
        "callsign_format": [
            r"[A-Z]{2,3}\s?\d{1,4}[A-Z]?",
            r"[A-Z]+\s?\d+"
        ],
        "altitude_readback": [
            r"(climb|descend|maintain)\s+to\s+(\d+)\s*(feet|ft)",
            r"(\d+)\s*(feet|ft)"
        ],
        "heading_readback": [
            r"(turn|heading)\s+(left|right|to)\s+(\d{3})",
            r"heading\s+(\d{3})"
        ],
        "runway_readback": [
            r"runway\s+(\d{2}[LRC]?)",
            r"rw[xy]\s+(\d{2}[LRC]?)"
        ]
    }
    
    # Common phraseology errors
    COMMON_ERRORS = {
        "yes": "affirmative",
        "no": "negative",
        "ok": "roger",
        "got it": "roger",
        "understand": "roger"
    }
    
    def validate_phraseology(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate phraseology in text
        
        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        text_lower = text.lower()
        
        # Check for common non-standard phrases
        for error, correct in self.COMMON_ERRORS.items():
            if error in text_lower:
                errors.append(f"Use '{correct}' instead of '{error}'")
        
        # Check for proper readback format
        if not self._has_proper_readback(text):
            errors.append("Missing proper readback format")
        
        return len(errors) == 0, errors
    
    def _has_proper_readback(self, text: str) -> bool:
        """Check if text contains proper readback elements"""
        text_lower = text.lower()
        
        # Check for acknowledgment
        has_ack = any(pattern in text_lower for pattern in 
                     ["roger", "wilco", "affirmative", "negative"])
        
        # Check for information repetition
        has_info = any(keyword in text_lower for keyword in
                      ["runway", "heading", "altitude", "taxi", "cleared"])
        
        return has_ack or has_info


class ReadbackValidator:
    """Validates readback accuracy"""

    _ACK_TOKENS = frozenset({
        "roger", "wilco", "affirmative", "negative", "copy", "copied",
        "thanks", "thank", "you",
    })

    # ICAO designator -> radiotelephony word (lowercase) for callsign readback tolerance
    _ICAO_TELEPHONY = {
        "SIA": "singapore",
        "MAS": "malaysia",
        "BAW": "speedbird",
        "UAL": "united",
        "DLH": "lufthansa",
        "AFR": "airfrans",
        "UAE": "emirates",
        "QFA": "qantas",
        "THA": "thai",
        "JAL": "japanair",
        "ANA": "allnippon",
        "CPA": "cathay",
        "EVA": "eva",
        "CAL": "dynasty",
        "AAL": "american",
        "DAL": "delta",
        "SWA": "southwest",
        "RYR": "ryanair",
        "EZY": "easy",
    }

    def validate_readback(
        self,
        instruction: str,
        readback: str,
        callsign: Optional[str] = None,
    ) -> Tuple[float, List[CommunicationError]]:
        """
        Validate readback against instruction

        Returns:
            Tuple of (accuracy_score 0-100, list of errors)
        """
        errors: List[CommunicationError] = []
        score = 100.0

        instruction_lower = instruction.lower()
        readback_lower = readback.lower()

        key_info = self._extract_key_information(instruction)

        safety_critical = bool(key_info) or self._instruction_has_safety_critical_language(instruction_lower)

        if safety_critical and self._is_acknowledgment_only(readback_lower):
            errors.append(
                CommunicationError(
                    error_type=ErrorType.READBACK_ERROR,
                    severity=ErrorSeverity.MAJOR,
                    message="Acknowledgment alone is not sufficient; read back safety-critical clearance elements.",
                    actual=readback,
                )
            )
            score -= 40.0

        for key, value in key_info.items():
            if not self._check_info_present(readback_lower, key, value):
                errors.append(
                    CommunicationError(
                        error_type=ErrorType.MISSING_INFORMATION,
                        severity=ErrorSeverity.MODERATE,
                        message=f"Missing {key} in readback",
                        expected=value,
                        actual=None,
                    )
                )
                score -= 15

        for error in self._check_incorrect_information(instruction, readback):
            errors.append(error)
            score -= 20

        cs = callsign.strip() if callsign else ""
        if cs and self._instruction_addresses_aircraft(instruction, cs):
            if not self._readback_includes_callsign(readback, cs):
                errors.append(
                    CommunicationError(
                        error_type=ErrorType.READBACK_ERROR,
                        severity=ErrorSeverity.MINOR,
                        message="Callsign missing or incomplete in readback",
                        expected=cs,
                        actual=readback,
                    )
                )
                score -= 10.0

        score = max(0.0, score)
        return score, errors

    def _instruction_addresses_aircraft(self, instruction: str, callsign: str) -> bool:
        ins_u = re.sub(r"\s+", "", instruction.upper())
        cs = callsign.upper().replace(" ", "")
        if len(cs) < 2:
            return False
        if cs in ins_u:
            return True
        m = re.match(r"^([A-Z]{2,3})(\d{1,4}[A-Z]?)$", cs)
        if m:
            compact = m.group(1) + m.group(2)
            spaced = m.group(1) + " " + m.group(2)
            return compact in ins_u or spaced.replace(" ", "") in ins_u
        return False

    def _instruction_has_safety_critical_language(self, instruction_lower: str) -> bool:
        """True when instruction likely requires full readback (not ack-only)."""
        if re.search(r"runway\s+\d{2}", instruction_lower):
            return True
        if re.search(r"\bheading\s+\d{3}", instruction_lower):
            return True
        if re.search(r"\d+\s*(feet|ft)\b|flight\s+level\s*\d+|maintain\s+\d+", instruction_lower):
            return True
        if "hold short" in instruction_lower:
            return True
        if re.search(r"\d{3}\.\d{2,3}", instruction_lower):
            return True
        if re.search(r"squawk\s+\d{4}", instruction_lower):
            return True
        if re.search(
            r"cleared\s+(?:for\s+)?(?:takeoff|landing|approach)|cleared\s+to\s+land\b",
            instruction_lower,
        ):
            return True
        return False

    def _is_acknowledgment_only(self, readback_lower: str) -> bool:
        cleaned = re.sub(r"[\.,!?]", " ", readback_lower)
        tokens = [t for t in cleaned.split() if t]
        return bool(tokens) and all(t in self._ACK_TOKENS for t in tokens)

    def _readback_includes_callsign(self, readback: str, callsign: str) -> bool:
        rb = readback.upper().replace(" ", "")
        cs = callsign.upper().replace(" ", "")
        if len(cs) < 2:
            return True
        if cs in rb.replace("-", ""):
            return True
        m = re.match(r"^([A-Z]{2,3})(\d{1,4}[A-Z]?)$", cs)
        if m:
            compact = m.group(1) + m.group(2)
            spaced = f"{m.group(1)} {m.group(2)}"
            rb_comp = rb.replace("-", "")
            if compact in rb_comp or spaced.replace(" ", "").upper() in rb_comp:
                return True
            telly = self._ICAO_TELEPHONY.get(m.group(1))
            num = m.group(2)
            if telly and re.search(
                rf"\b{re.escape(telly)}\s+{re.escape(num)}\b",
                readback.lower(),
            ):
                return True
        return False

    def _extract_key_information(self, instruction: str) -> Dict[str, str]:
        """Extract key information from instruction"""
        info: Dict[str, str] = {}

        if not instruction or not isinstance(instruction, str):
            return info

        instruction_lower = instruction.lower()

        runway_match = re.search(r"runway\s+(\d{2}[LRC]?)", instruction_lower)
        if runway_match:
            info["runway"] = runway_match.group(1)

        heading_match = re.search(
            r"(?:heading|turn\s+(?:left|right)\s+(?:to\s+)?(?:heading\s+)?)(\d{3})", instruction_lower
        )
        if heading_match:
            info["heading"] = heading_match.group(1)

        alt_match = re.search(r"(?:flight\s+level\s+|FL\s*)(\d{3})\b", instruction_lower)
        if alt_match:
            info["altitude"] = alt_match.group(1)
        else:
            alt_match = re.search(
                r"(?:climb|descend|maintain)\s+(?:to\s+)?(\d{3,5})\s*(?:feet|ft)?", instruction_lower
            )
            if alt_match:
                info["altitude"] = alt_match.group(1)

        taxi_match = re.search(r"taxi(?:way)?\s+([A-Z]+)", instruction_lower)
        if taxi_match:
            info["taxiway"] = taxi_match.group(1)

        freq_match = re.search(r"(\d{3}\.\d{2,3})", instruction)
        if freq_match:
            info["frequency"] = ReadbackValidator._normalize_frequency_token(freq_match.group(1))

        squawk_match = re.search(r"squawk\s+(\d{4})", instruction_lower)
        if squawk_match:
            info["squawk"] = squawk_match.group(1)

        if "hold short" in instruction_lower:
            hs_rw = re.search(r"hold\s+short\s+(?:of\s+)?runway\s+(\d{2}[LRC]?)", instruction_lower)
            info["hold_short"] = hs_rw.group(1) if hs_rw else "short"

        return info

    @staticmethod
    def _normalize_frequency_token(freq: str) -> str:
        """Normalize 134.9 vs 134.90 for comparison."""
        if not freq:
            return freq
        try:
            return f"{float(freq):.4f}".rstrip("0").rstrip(".")
        except ValueError:
            return freq

    def _check_info_present(self, readback: str, key: str, value: str) -> bool:
        """Check if key information is present in readback"""
        if key == "runway":
            return bool(re.search(rf"runway\s+{value}", readback, re.IGNORECASE))
        elif key == "heading":
            return bool(re.search(rf"(?:heading\s+{value}|turn\s+.*{value})", readback, re.IGNORECASE))
        elif key == "altitude":
            return bool(re.search(rf"{value}\s*(?:feet|ft|FL)|FL\s*{value}", readback, re.IGNORECASE))
        elif key == "taxiway":
            return bool(re.search(rf"taxi(?:way)?\s+{value}", readback, re.IGNORECASE))
        elif key == "frequency":
            m = re.search(r"(\d{3}\.\d{2,3})", readback)
            if not m:
                return False
            return self._normalize_frequency_token(m.group(1)) == self._normalize_frequency_token(value)
        elif key == "squawk":
            return bool(re.search(rf"squawk\s+{value}|(?:^|\s){value}(?:\s|$)", readback, re.IGNORECASE))
        elif key == "hold_short":
            if value == "short":
                return "hold short" in readback.lower()
            return "hold short" in readback.lower() and bool(
                re.search(rf"runway\s+{value}", readback, re.IGNORECASE)
            )
        return False
    
    def _check_incorrect_information(self, 
                                    instruction: str, 
                                    readback: str) -> List[CommunicationError]:
        """Check for incorrect information in readback"""
        errors = []
        
        # Extract values from both
        inst_info = self._extract_key_information(instruction)
        read_info = self._extract_key_information(readback)
        
        # Compare (normalized where appropriate)
        for key, inst_value in inst_info.items():
            if key not in read_info:
                continue
            rb_val = read_info[key]
            if key == "frequency":
                if self._normalize_frequency_token(rb_val) != self._normalize_frequency_token(inst_value):
                    errors.append(
                        CommunicationError(
                            error_type=ErrorType.INCORRECT_INFORMATION,
                            severity=ErrorSeverity.MAJOR,
                            message=f"Incorrect {key} in readback",
                            expected=inst_value,
                            actual=read_info[key],
                        )
                    )
            elif key == "runway" and inst_value.upper() == rb_val.upper():
                continue
            elif rb_val != inst_value:
                errors.append(
                    CommunicationError(
                        error_type=ErrorType.INCORRECT_INFORMATION,
                        severity=ErrorSeverity.MAJOR,
                        message=f"Incorrect {key} in readback",
                        expected=inst_value,
                        actual=read_info[key],
                    )
                )

        return errors


class AssessmentEngine:
    """Main assessment engine for pilot training"""

    def __init__(self):
        """Initialize the assessment engine"""
        self.phraseology_validator = PhraseologyValidator()
        self.readback_validator = ReadbackValidator()
        self.communication_history: List[Dict[str, Any]] = []
        self.response_times: List[float] = []

    def _score_communication_record(
        self,
        instruction: str,
        readback: str,
        response_time: Optional[float] = None,
        callsign: Optional[str] = None,
    ) -> AssessmentResult:
        """
        Pure assessment for one exchange: does not append to communication_history or response_times.
        """
        errors: List[CommunicationError] = []
        strengths: List[str] = []
        recommendations: List[str] = []

        phraseology_valid, phraseology_errors = self.phraseology_validator.validate_phraseology(readback)
        if not phraseology_valid:
            for error_msg in phraseology_errors:
                errors.append(
                    CommunicationError(
                        error_type=ErrorType.PHRASEOLOGY_ERROR,
                        severity=ErrorSeverity.MINOR,
                        message=error_msg,
                        actual=readback,
                    )
                )

        readback_score, readback_errors = self.readback_validator.validate_readback(
            instruction, readback, callsign=callsign
        )
        errors.extend(readback_errors)

        phraseology_score = 100.0 if phraseology_valid else 70.0
        overall_score = readback_score * 0.7 + phraseology_score * 0.3

        if readback_score >= 90:
            strengths.append("Excellent readback accuracy")
        if phraseology_valid:
            strengths.append("Proper phraseology usage")
        if response_time is not None and response_time < 3.0:
            strengths.append("Quick response time")

        if readback_score < 70:
            recommendations.append("Practice reading back all key information from instructions")
        if not phraseology_valid:
            recommendations.append("Review standard ATC phraseology")
        if response_time is not None and response_time > 5.0:
            recommendations.append("Work on reducing response time")

        return AssessmentResult(
            score=overall_score,
            errors=errors,
            strengths=strengths,
            recommendations=recommendations,
            accuracy_percentage=readback_score,
            response_time_avg=0.0,
            phraseology_score=phraseology_score,
            readback_score=readback_score,
        )

    def assess_communication(
        self,
        instruction: str,
        readback: str,
        response_time: Optional[float] = None,
        callsign: Optional[str] = None,
    ) -> AssessmentResult:
        """
        Assess a pilot communication

        Args:
            instruction: ATC instruction
            readback: Pilot readback
            response_time: Time taken to respond (seconds)
            callsign: Optional aircraft callsign for readback checks when ATC addresses this aircraft

        Returns:
            AssessmentResult with scores and feedback
        """
        if response_time is not None:
            self.response_times.append(response_time)

        result = self._score_communication_record(
            instruction, readback, response_time=response_time, callsign=callsign
        )

        response_time_avg = (
            sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        )
        result.response_time_avg = response_time_avg

        self.communication_history.append(
            {
                "instruction": instruction,
                "readback": readback,
                "timestamp": time.time(),
                "response_time": response_time,
                "score": result.score,
                "callsign": callsign,
            }
        )

        return result

    def assess_session(self) -> AssessmentResult:
        """Assess entire training session"""
        if not self.communication_history:
            return AssessmentResult(
                score=0.0,
                errors=[],
                strengths=[],
                recommendations=["No communications to assess"],
            )

        history_snapshot = list(self.communication_history)

        total_score = sum(comm.get("score", 0.0) for comm in history_snapshot)
        avg_score = total_score / len(history_snapshot) if history_snapshot else 0.0

        all_errors: List[CommunicationError] = []
        merged_strengths: List[str] = []
        merged_recommendations: List[str] = []

        for comm in history_snapshot:
            instruction = comm.get("instruction")
            readback = comm.get("readback")
            if not instruction or not isinstance(instruction, str):
                continue
            if not readback or not isinstance(readback, str):
                continue

            try:
                result = self._score_communication_record(
                    instruction,
                    readback,
                    response_time=comm.get("response_time"),
                    callsign=comm.get("callsign"),
                )
                all_errors.extend(result.errors)
                merged_strengths.extend(result.strengths)
                merged_recommendations.extend(result.recommendations)
            except Exception as e:
                logger.warning("Failed to assess communication: %r", e)
                continue

        response_time_values = [
            comm.get("response_time")
            for comm in history_snapshot
            if comm.get("response_time") is not None
        ]
        avg_response_time = (
            sum(response_time_values) / len(response_time_values) if response_time_values else 0.0
        )

        recommendations = []
        seen_r: set = set()
        for r in merged_recommendations:
            if r not in seen_r:
                seen_r.add(r)
                recommendations.append(r)
        if avg_score < 70:
            recommendations.append("Overall performance needs improvement. Review ATC procedures.")
        if len(all_errors) > 5:
            recommendations.append("High number of errors. Consider additional training.")

        strengths_session: List[str] = []
        seen_s: set = set()
        for s in merged_strengths:
            if s not in seen_s:
                seen_s.add(s)
                strengths_session.append(s)
        strengths_session = strengths_session[:10]

        return AssessmentResult(
            score=avg_score,
            errors=all_errors,
            strengths=strengths_session,
            recommendations=recommendations,
            accuracy_percentage=avg_score,
            response_time_avg=avg_response_time,
            phraseology_score=avg_score,
            readback_score=avg_score,
            metadata={
                "total_communications": len(history_snapshot),
                "error_count": len(all_errors),
            },
        )

    def reset_session(self):
        """Reset assessment for new session"""
        self.communication_history.clear()
        self.response_times.clear()

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by type"""
        summary = {error_type.value: 0 for error_type in ErrorType}

        for comm in list(self.communication_history):
            instruction = comm.get("instruction") or ""
            readback = comm.get("readback") or ""
            try:
                result = self._score_communication_record(
                    instruction,
                    readback,
                    response_time=comm.get("response_time"),
                    callsign=comm.get("callsign"),
                )
                for error in result.errors:
                    summary[error.error_type.value] += 1
            except Exception as e:
                logger.warning("Failed to summarize errors for communication: %r", e)
                continue

        return summary
