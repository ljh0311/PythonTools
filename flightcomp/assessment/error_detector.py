"""
Error Detection System for Pilot Training
Identifies and categorizes errors in pilot communications and procedures
"""

import re
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from .assessment_engine import ErrorType, ErrorSeverity, CommunicationError


class ErrorPattern:
    """Pattern for detecting specific errors"""
    
    def __init__(self, 
                 error_type: ErrorType,
                 pattern: str,
                 severity: ErrorSeverity,
                 description: str):
        self.error_type = error_type
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.severity = severity
        self.description = description
    
    def match(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Check if pattern matches text
        
        Returns:
            Tuple of (matched_text, context) if match found, None otherwise
        """
        match = self.pattern.search(text)
        if match:
            return (match.group(0), text[max(0, match.start()-20):match.end()+20])
        return None


class ErrorDetector:
    """Detects errors in pilot communications"""
    
    def __init__(self):
        """Initialize error detector with patterns"""
        self.error_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> List[ErrorPattern]:
        """Initialize error detection patterns"""
        patterns = [
            # Phraseology errors
            ErrorPattern(
                ErrorType.PHRASEOLOGY_ERROR,
                r"\b(yes|no|ok|got it|understand)\b",
                ErrorSeverity.MINOR,
                "Non-standard phraseology"
            ),
            ErrorPattern(
                ErrorType.PHRASEOLOGY_ERROR,
                r"\b(yeah|yep|nope|sure)\b",
                ErrorSeverity.MINOR,
                "Informal language"
            ),
            
            # Missing information patterns
            ErrorPattern(
                ErrorType.MISSING_INFORMATION,
                r"roger\s*$",
                ErrorSeverity.MODERATE,
                "Readback missing key information"
            ),
            
            # Incorrect information patterns
            ErrorPattern(
                ErrorType.INCORRECT_INFORMATION,
                r"runway\s+(\d{2}[LRC]?)\s+.*runway\s+(\d{2}[LRC]?)",
                ErrorSeverity.MAJOR,
                "Conflicting runway information"
            ),
            
            # Timing errors (detected separately, but pattern for context)
            ErrorPattern(
                ErrorType.TIMING_ERROR,
                r"(immediately|right now|asap)",
                ErrorSeverity.MODERATE,
                "Urgency indicator - check timing"
            ),
            
            # Procedure errors
            ErrorPattern(
                ErrorType.PROCEDURE_ERROR,
                r"(cleared|approved).*without.*(checklist|briefing)",
                ErrorSeverity.MAJOR,
                "Procedure skipped"
            ),
        ]
        return patterns
    
    def detect_errors(self, 
                     instruction: str,
                     readback: str,
                     context: Optional[Dict] = None) -> List[CommunicationError]:
        """
        Detect errors in communication
        
        Args:
            instruction: ATC instruction
            readback: Pilot readback
            context: Additional context (response time, etc.)
        
        Returns:
            List of detected errors
        """
        errors = []
        
        # Check readback against patterns
        for pattern in self.error_patterns:
            match_result = pattern.match(readback)
            if match_result:
                matched_text, match_context = match_result
                errors.append(CommunicationError(
                    error_type=pattern.error_type,
                    severity=pattern.severity,
                    message=pattern.description,
                    actual=matched_text,
                    context={"match_context": match_context}
                ))
        
        # Check for missing critical information
        missing_errors = self._check_missing_critical_info(instruction, readback)
        errors.extend(missing_errors)
        
        # Check for incorrect information
        incorrect_errors = self._check_incorrect_info(instruction, readback)
        errors.extend(incorrect_errors)
        
        # Check timing if context provided
        if context and "response_time" in context:
            timing_errors = self._check_timing(context["response_time"])
            errors.extend(timing_errors)
        
        return errors
    
    def _check_missing_critical_info(self, 
                                    instruction: str, 
                                    readback: str) -> List[CommunicationError]:
        """Check for missing critical information"""
        errors = []
        
        # Critical information keywords
        critical_keywords = {
            "runway": r"runway\s+(\d{2}[LRC]?)",
            "altitude": r"(\d+)\s*(feet|ft|FL)",
            "heading": r"heading\s+(\d{3})",
            "frequency": r"(\d{3}\.\d+)",
            "squawk": r"squawk\s+(\d{4})"
        }
        
        instruction_lower = instruction.lower()
        readback_lower = readback.lower()
        
        for keyword, pattern in critical_keywords.items():
            if re.search(pattern, instruction_lower):
                if not re.search(pattern, readback_lower):
                    errors.append(CommunicationError(
                        error_type=ErrorType.MISSING_INFORMATION,
                        severity=ErrorSeverity.MODERATE,
                        message=f"Missing {keyword} in readback",
                        expected=f"{keyword} from instruction",
                        actual=None
                    ))
        
        return errors
    
    def _check_incorrect_info(self, 
                             instruction: str, 
                             readback: str) -> List[CommunicationError]:
        """Check for incorrect information"""
        errors = []
        
        # Extract values from instruction
        inst_runway = re.search(r"runway\s+(\d{2}[LRC]?)", instruction.lower())
        read_runway = re.search(r"runway\s+(\d{2}[LRC]?)", readback.lower())
        
        if inst_runway and read_runway:
            if inst_runway.group(1) != read_runway.group(1):
                errors.append(CommunicationError(
                    error_type=ErrorType.INCORRECT_INFORMATION,
                    severity=ErrorSeverity.MAJOR,
                    message="Incorrect runway in readback",
                    expected=inst_runway.group(1),
                    actual=read_runway.group(1)
                ))
        
        # Check altitude
        inst_alt = re.search(r"(\d+)\s*(feet|ft|FL)", instruction.lower())
        read_alt = re.search(r"(\d+)\s*(feet|ft|FL)", readback.lower())
        
        if inst_alt and read_alt:
            if inst_alt.group(1) != read_alt.group(1):
                errors.append(CommunicationError(
                    error_type=ErrorType.INCORRECT_INFORMATION,
                    severity=ErrorSeverity.MAJOR,
                    message="Incorrect altitude in readback",
                    expected=inst_alt.group(1),
                    actual=read_alt.group(1)
                ))
        
        return errors
    
    def _check_timing(self, response_time: float) -> List[CommunicationError]:
        """Check for timing errors"""
        errors = []
        
        # Response time thresholds (seconds)
        if response_time > 10.0:
            errors.append(CommunicationError(
                error_type=ErrorType.TIMING_ERROR,
                severity=ErrorSeverity.MODERATE,
                message="Response time too slow",
                actual=f"{response_time:.1f} seconds"
            ))
        elif response_time < 0.5:
            errors.append(CommunicationError(
                error_type=ErrorType.TIMING_ERROR,
                severity=ErrorSeverity.MINOR,
                message="Response time unusually fast - ensure complete readback",
                actual=f"{response_time:.1f} seconds"
            ))
        
        return errors
    
    def categorize_errors(self, errors: List[CommunicationError]) -> Dict[ErrorType, List[CommunicationError]]:
        """Categorize errors by type"""
        categorized = {error_type: [] for error_type in ErrorType}
        
        for error in errors:
            categorized[error.error_type].append(error)
        
        return categorized
    
    def get_error_statistics(self, errors: List[CommunicationError]) -> Dict[str, int]:
        """Get statistics about errors"""
        stats = {
            "total": len(errors),
            "by_type": {},
            "by_severity": {}
        }
        
        for error_type in ErrorType:
            stats["by_type"][error_type.value] = sum(
                1 for e in errors if e.error_type == error_type
            )
        
        for severity in ErrorSeverity:
            stats["by_severity"][severity.value] = sum(
                1 for e in errors if e.severity == severity
            )
        
        return stats

