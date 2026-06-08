"""
Scoring Rubric for Pilot Training Assessment
Defines scoring criteria and weights for different aspects of pilot performance
"""

from typing import Dict, List
from dataclasses import dataclass
from enum import Enum


class SkillCategory(Enum):
    """Categories of pilot skills"""
    COMMUNICATION = "communication"
    PROCEDURES = "procedures"
    SITUATIONAL_AWARENESS = "situational_awareness"
    DECISION_MAKING = "decision_making"
    EMERGENCY_HANDLING = "emergency_handling"


@dataclass
class ScoringCriteria:
    """Scoring criteria for a skill category"""
    category: SkillCategory
    weight: float  # 0.0 to 1.0
    max_score: float = 100.0
    criteria: Dict[str, float] = None  # Sub-criteria with weights
    
    def __post_init__(self):
        if self.criteria is None:
            self.criteria = {}


class ScoringRubric:
    """Rubric for scoring pilot performance"""
    
    def __init__(self):
        """Initialize with default scoring rubric"""
        self.criteria = {
            SkillCategory.COMMUNICATION: ScoringCriteria(
                category=SkillCategory.COMMUNICATION,
                weight=0.35,
                criteria={
                    "phraseology": 0.4,
                    "readback_accuracy": 0.4,
                    "response_time": 0.2
                }
            ),
            SkillCategory.PROCEDURES: ScoringCriteria(
                category=SkillCategory.PROCEDURES,
                weight=0.25,
                criteria={
                    "checklist_completion": 0.3,
                    "sequence_correctness": 0.4,
                    "timing": 0.3
                }
            ),
            SkillCategory.SITUATIONAL_AWARENESS: ScoringCriteria(
                category=SkillCategory.SITUATIONAL_AWARENESS,
                weight=0.20,
                criteria={
                    "traffic_awareness": 0.4,
                    "position_awareness": 0.3,
                    "weather_awareness": 0.3
                }
            ),
            SkillCategory.DECISION_MAKING: ScoringCriteria(
                category=SkillCategory.DECISION_MAKING,
                weight=0.15,
                criteria={
                    "decision_quality": 0.5,
                    "decision_speed": 0.3,
                    "risk_assessment": 0.2
                }
            ),
            SkillCategory.EMERGENCY_HANDLING: ScoringCriteria(
                category=SkillCategory.EMERGENCY_HANDLING,
                weight=0.05,
                criteria={
                    "emergency_recognition": 0.3,
                    "procedure_execution": 0.4,
                    "communication": 0.3
                }
            )
        }
    
    def calculate_weighted_score(self, scores: Dict[SkillCategory, float]) -> float:
        """
        Calculate weighted overall score
        
        Args:
            scores: Dictionary of category scores
        
        Returns:
            Weighted overall score (0-100)
        """
        total_score = 0.0
        
        for category, criteria in self.criteria.items():
            if category in scores:
                category_score = scores[category]
                weighted_score = category_score * criteria.weight
                total_score += weighted_score
        
        return total_score
    
    def get_category_weights(self) -> Dict[SkillCategory, float]:
        """Get weights for each category"""
        return {cat: crit.weight for cat, crit in self.criteria.items()}
    
    def get_criteria_for_category(self, category: SkillCategory) -> ScoringCriteria:
        """Get scoring criteria for a specific category"""
        return self.criteria.get(category)
    
    def adjust_weights(self, category: SkillCategory, new_weight: float):
        """Adjust weight for a category"""
        if category in self.criteria:
            self.criteria[category].weight = new_weight
            # Normalize weights to sum to 1.0
            self._normalize_weights()
    
    def _normalize_weights(self):
        """Normalize weights so they sum to 1.0"""
        total_weight = sum(crit.weight for crit in self.criteria.values())
        if total_weight > 0:
            for criteria in self.criteria.values():
                criteria.weight /= total_weight

