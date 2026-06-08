"""
Phraseology Validator for AI Responses
Enforces standard ATC phraseology in AI-generated responses
"""

import re
from typing import List, Tuple, Dict, Optional
from enum import Enum


class PhraseologyStandard(Enum):
    """Phraseology standards"""
    ICAO = "icao"
    FAA = "faa"
    UK = "uk"
    CUSTOM = "custom"


class PhraseologyValidator:
    """Validates and enforces ATC phraseology"""
    
    # Standard phraseology patterns
    STANDARD_PHRASES = {
        "acknowledgment": [
            r"roger",
            r"wilco",
            r"affirmative",
            r"negative",
            r"standby"
        ],
        "clearance": [
            r"cleared\s+(?:for\s+)?(?:takeoff|landing|taxi|approach)",
            r"cleared\s+to\s+(?:land|takeoff|taxi)"
        ],
        "instruction": [
            r"taxi\s+(?:to|via)",
            r"turn\s+(?:left|right|heading)",
            r"climb\s+(?:to|and\s+maintain)",
            r"descend\s+(?:to|and\s+maintain)",
            r"maintain\s+(?:altitude|heading|speed|flight\s+level)",
            r"cleared\s+via\s+(?:SID|STAR)",
            r"descend\s+via\s+STAR",
            r"cross\s+\w+\s+at",
            r"hold\s+at",
            r"pushback\s+approved",
            r"start\s+approved"
        ],
        "frequency": [
            r"contact\s+(?:ground|tower|approach|departure)\s+on\s+\d{3}\.\d+",
            r"switch\s+to\s+\d{3}\.\d+"
        ],
        "runway": [
            r"runway\s+\d{2}[LRC]?",
            r"rw[xy]\s+\d{2}[LRC]?"
        ],
        "commercial": [
            r"flight\s+level\s+\d{3}",
            r"FL\s+\d{3}",
            r"SID\s+\w+",
            r"STAR\s+\w+",
            r"waypoint\s+\w+",
            r"reduce\s+speed\s+to",
            r"increase\s+speed\s+to",
            r"go\s+around",
            r"missed\s+approach"
        ]
    }
    
    # Non-standard phrases to avoid
    NON_STANDARD_PHRASES = [
        r"\b(?:yes|no|ok|sure|got it|understand)\b",
        r"\b(?:please|thank you|thanks)\b",  # Too informal for ATC
        r"\b(?:can you|could you|would you)\b"  # Too polite
    ]
    
    def __init__(self, standard: PhraseologyStandard = PhraseologyStandard.ICAO):
        """Initialize phraseology validator"""
        self.standard = standard
    
    def validate_response(self, response: str) -> Tuple[bool, List[str]]:
        """
        Validate ATC response phraseology
        
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        response_lower = response.lower()
        
        # Check for non-standard phrases
        for pattern in self.NON_STANDARD_PHRASES:
            if re.search(pattern, response_lower):
                issues.append(f"Non-standard phraseology detected: {pattern}")
        
        # Check for proper structure
        if not self._has_proper_structure(response):
            issues.append("Response lacks proper ATC structure")
        
        # Check for callsign usage
        if not self._has_callsign(response):
            issues.append("Response should include aircraft callsign")
        
        return len(issues) == 0, issues
    
    def enforce_phraseology(self, response: str) -> str:
        """
        Enforce standard phraseology in response
        
        Returns:
            Corrected response
        """
        corrected = response
        
        # Replace non-standard phrases
        replacements = {
            r"\byes\b": "affirmative",
            r"\bno\b": "negative",
            r"\bok\b": "roger",
            r"\bsure\b": "roger",
            r"\bgot it\b": "roger",
            r"\bunderstand\b": "roger"
        }
        
        for pattern, replacement in replacements.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        # Ensure proper capitalization
        corrected = self._capitalize_aviation_terms(corrected)
        
        return corrected
    
    def _has_proper_structure(self, response: str) -> bool:
        """Check if response has proper ATC structure"""
        # Should start with callsign or instruction
        has_callsign = bool(re.search(r"^[A-Z]{2,3}\s?\d+", response, re.IGNORECASE))
        has_instruction = any(
            re.search(pattern, response, re.IGNORECASE)
            for patterns in self.STANDARD_PHRASES.values()
            for pattern in patterns
        )
        
        return has_callsign or has_instruction
    
    def _has_callsign(self, response: str) -> bool:
        """Check if response includes a callsign"""
        # Look for callsign pattern
        return bool(re.search(r"[A-Z]{2,3}\s?\d+[A-Z]?", response))
    
    def _capitalize_aviation_terms(self, text: str) -> str:
        """Capitalize standard aviation terms"""
        terms = [
            "Runway", "Taxiway", "Heading", "Altitude", "Speed",
            "Cleared", "Roger", "Wilco", "Affirmative", "Negative"
        ]
        
        for term in terms:
            text = re.sub(rf"\b{term.lower()}\b", term, text, flags=re.IGNORECASE)
        
        return text
    
    def suggest_improvements(self, response: str) -> List[str]:
        """Suggest improvements to response"""
        suggestions = []
        response_lower = response.lower()
        
        # Check for missing elements
        if "cleared" in response_lower and "runway" not in response_lower:
            if "takeoff" in response_lower or "landing" in response_lower:
                suggestions.append("Specify runway number in clearance")
        
        if "taxi" in response_lower and "via" not in response_lower and "to" not in response_lower:
            suggestions.append("Specify taxi route (via taxiway or to location)")
        
        if "contact" in response_lower and not re.search(r"\d{3}\.\d+", response):
            suggestions.append("Include frequency when instructing contact")
        
        return suggestions

