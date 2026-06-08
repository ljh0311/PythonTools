"""
Training Record Model
Stores training session data and progress tracking information
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


_ERROR_TYPE_LABELS = {
    "phraseology_error": "Phraseology",
    "readback_error": "Readback",
    "missing_information": "Missing information",
    "incorrect_information": "Incorrect information",
    "timing_error": "Timing",
    "procedure_error": "Procedure",
}


# Current data format version for session and pilot JSON; used for migrations.
DATA_VERSION = 1
# Maximum number of recent scores kept in SkillProgress.trend.
TREND_HISTORY_MAX = 20


class SessionStatus(Enum):
    """Status of a training session"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PAUSED = "paused"


@dataclass
class CommunicationRecord:
    """Record of a single communication"""
    instruction: str
    readback: str
    timestamp: float
    response_time: Optional[float] = None
    score: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CommunicationRecord':
        """Create from dictionary"""
        return CommunicationRecord(
            instruction=data["instruction"],
            readback=data["readback"],
            timestamp=data["timestamp"],
            response_time=data.get("response_time"),
            score=data.get("score", 0.0),
            errors=data.get("errors", [])
        )


@dataclass
class TrainingSession:
    """Represents a training session"""
    session_id: str
    pilot_id: Optional[str] = None
    scenario_id: Optional[str] = None
    airport_icao: str = ""
    difficulty: str = "beginner"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SessionStatus = SessionStatus.IN_PROGRESS
    communications: List[CommunicationRecord] = field(default_factory=list)
    overall_score: float = 0.0
    skill_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "data_version": DATA_VERSION,
            "session_id": self.session_id,
            "pilot_id": self.pilot_id,
            "scenario_id": self.scenario_id,
            "airport_icao": self.airport_icao,
            "difficulty": self.difficulty,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "communications": [comm.to_dict() for comm in self.communications],
            "overall_score": self.overall_score,
            "skill_scores": self.skill_scores,
            "metadata": self.metadata
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TrainingSession':
        """Create from dictionary. Validates required fields; missing data_version treated as 1."""
        if "session_id" not in data:
            raise ValueError("TrainingSession JSON missing required field: session_id")
        return TrainingSession(
            session_id=data["session_id"],
            pilot_id=data.get("pilot_id"),
            scenario_id=data.get("scenario_id"),
            airport_icao=data.get("airport_icao", ""),
            difficulty=data.get("difficulty", "beginner"),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time"),
            status=SessionStatus(data.get("status", "in_progress")),
            communications=[CommunicationRecord.from_dict(c) for c in data.get("communications", [])],
            overall_score=data.get("overall_score", 0.0),
            skill_scores=data.get("skill_scores", {}),
            metadata=data.get("metadata", {})
        )
    
    def add_communication(self, communication: CommunicationRecord):
        """Add a communication to the session"""
        self.communications.append(communication)
    
    def complete_session(self, overall_score: float, skill_scores: Dict[str, float]):
        """Mark session as completed"""
        self.status = SessionStatus.COMPLETED
        self.end_time = time.time()
        self.overall_score = overall_score
        self.skill_scores = skill_scores
    
    def get_duration(self) -> float:
        """Get session duration in seconds"""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    def get_communication_count(self) -> int:
        """Get number of communications in session"""
        return len(self.communications)
    
    def get_average_score(self) -> float:
        """Get average score of communications"""
        if not self.communications:
            return 0.0
        return sum(comm.score for comm in self.communications) / len(self.communications)


@dataclass
class SkillProgress:
    """Progress tracking for a specific skill"""
    skill_name: str
    current_level: str = "beginner"
    sessions_completed: int = 0
    average_score: float = 0.0
    trend: List[float] = field(default_factory=list)  # Score history
    last_practiced: Optional[float] = None
    weak_areas: List[str] = field(default_factory=list)
    strong_areas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SkillProgress':
        """Create from dictionary"""
        return SkillProgress(
            skill_name=data["skill_name"],
            current_level=data.get("current_level", "beginner"),
            sessions_completed=data.get("sessions_completed", 0),
            average_score=data.get("average_score", 0.0),
            trend=data.get("trend", []),
            last_practiced=data.get("last_practiced"),
            weak_areas=data.get("weak_areas", []),
            strong_areas=data.get("strong_areas", [])
        )
    
    def update_score(self, score: float) -> None:
        """Update skill with new score; trim trend to TREND_HISTORY_MAX and recalculate level."""
        self.trend.append(score)
        if len(self.trend) > TREND_HISTORY_MAX:
            self.trend = self.trend[-TREND_HISTORY_MAX:]
        
        # Recalculate average
        self.average_score = sum(self.trend) / len(self.trend)
        self.last_practiced = time.time()
        
        # Update level based on average
        if self.average_score >= 90:
            self.current_level = "expert"
        elif self.average_score >= 75:
            self.current_level = "advanced"
        elif self.average_score >= 60:
            self.current_level = "intermediate"
        else:
            self.current_level = "beginner"


@dataclass
class PilotProgress:
    """Overall progress tracking for a pilot"""
    pilot_id: str
    total_sessions: int = 0
    total_communications: int = 0
    overall_average_score: float = 0.0
    skill_progress: Dict[str, SkillProgress] = field(default_factory=dict)
    session_history: List[str] = field(default_factory=list)  # Session IDs
    last_training_date: Optional[float] = None
    certifications: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "data_version": DATA_VERSION,
            "pilot_id": self.pilot_id,
            "total_sessions": self.total_sessions,
            "total_communications": self.total_communications,
            "overall_average_score": self.overall_average_score,
            "skill_progress": {k: v.to_dict() for k, v in self.skill_progress.items()},
            "session_history": self.session_history,
            "last_training_date": self.last_training_date,
            "certifications": self.certifications
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PilotProgress':
        """Create from dictionary. Validates required fields; missing data_version treated as 1."""
        if "pilot_id" not in data:
            raise ValueError("PilotProgress JSON missing required field: pilot_id")
        return PilotProgress(
            pilot_id=data["pilot_id"],
            total_sessions=data.get("total_sessions", 0),
            total_communications=data.get("total_communications", 0),
            overall_average_score=data.get("overall_average_score", 0.0),
            skill_progress={
                k: SkillProgress.from_dict(v) 
                for k, v in data.get("skill_progress", {}).items()
            },
            session_history=data.get("session_history", []),
            last_training_date=data.get("last_training_date"),
            certifications=data.get("certifications", [])
        )
    
    def update_with_session(self, session: TrainingSession):
        """Update progress with a completed session"""
        self.total_sessions += 1
        self.total_communications += session.get_communication_count()
        self.last_training_date = time.time()

        weak, strong = self._derive_weak_strong_from_session(session)

        # Update skill progress
        for skill_name, score in session.skill_scores.items():
            if skill_name not in self.skill_progress:
                self.skill_progress[skill_name] = SkillProgress(skill_name=skill_name)
            self.skill_progress[skill_name].update_score(score)
            self.skill_progress[skill_name].sessions_completed += 1
            sp = self.skill_progress[skill_name]
            if skill_name == "readback_accuracy":
                sp.weak_areas = [
                    w for w in weak if w in ("Readback", "Missing information", "Incorrect information")
                ] or weak[:3]
                if score >= 78:
                    sp.strong_areas = [s for s in strong if "readback" in s.lower()] or (
                        ["Readback scores on track"] if score >= 85 else strong[:2]
                    )
                else:
                    sp.strong_areas = []
            elif skill_name == "communication":
                sp.weak_areas = [
                    w for w in weak if w in ("Phraseology", "Timing", "Procedure")
                ] or weak[:3]
                ph = session.skill_scores.get("communication", score)
                if ph >= 78:
                    sp.strong_areas = [
                        s for s in strong if any(x in s.lower() for x in ("phraseology", "overall", "scores"))
                    ] or (["Communication scores on track"] if ph >= 85 else strong[:2])
                else:
                    sp.strong_areas = []
            else:
                sp.weak_areas = weak[:5]
                sp.strong_areas = strong[:4] if score >= 75 else []
        
        # Recalculate overall average
        if self.skill_progress:
            self.overall_average_score = sum(
                sp.average_score for sp in self.skill_progress.values()
            ) / len(self.skill_progress)
        
        # Add to session history
        self.session_history.append(session.session_id)
        # Keep only last 100 sessions
        if len(self.session_history) > 100:
            self.session_history = self.session_history[-100:]

    def _derive_weak_strong_from_session(self, session: TrainingSession) -> Tuple[List[str], List[str]]:
        """Derive weak/strong focus labels from recorded communication errors."""
        counts: Dict[str, int] = {}
        for comm in session.communications:
            for err in comm.errors:
                et = err.get("error_type") or "unknown"
                counts[et] = counts.get(et, 0) + 1

        weak = [
            _ERROR_TYPE_LABELS.get(k, k.replace("_", " ").title())
            for k, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        ]

        strong: List[str] = []
        avg = session.get_average_score()
        if avg >= 82 and session.communications:
            strong.append("Solid overall exchange scores")
        rb_comm_err = counts.get("readback_error", 0) + counts.get("missing_information", 0)
        if session.communications and rb_comm_err == 0:
            strong.append("Complete readbacks on recorded exchanges")
        if counts.get("phraseology_error", 0) == 0 and session.communications:
            strong.append("No phraseology flags in session log")

        return weak, strong

