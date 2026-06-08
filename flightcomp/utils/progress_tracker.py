"""
Progress Tracker for Pilot Training
Tracks training sessions, skill progression, and performance metrics
"""

import os
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from models.training_record import (
    TrainingSession,
    CommunicationRecord,
    SessionStatus,
    PilotProgress,
    SkillProgress
)
from assessment.assessment_engine import AssessmentResult
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """Tracks pilot training progress"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize progress tracker
        
        Args:
            data_dir: Directory to store progress data. Defaults to data/training_records/
        """
        if data_dir is None:
            # Default to data/training_records/ relative to project root
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(current_dir, "data", "training_records")
        
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.current_session: Optional[TrainingSession] = None
        self.pilot_progress: Dict[str, PilotProgress] = {}
        self._load_pilot_progress()
    
    def start_session(self,
                     pilot_id: str,
                     scenario_id: Optional[str] = None,
                     airport_icao: str = "",
                     difficulty: str = "beginner",
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new training session
        
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        self.current_session = TrainingSession(
            session_id=session_id,
            pilot_id=pilot_id,
            scenario_id=scenario_id,
            airport_icao=airport_icao,
            difficulty=difficulty,
            metadata=metadata or {}
        )
        
        return session_id
    
    def add_communication(self,
                         instruction: str,
                         readback: str,
                         assessment_result: AssessmentResult,
                         response_time: Optional[float] = None):
        """Add a communication to the current session"""
        if not self.current_session:
            raise ValueError("No active session. Call start_session() first.")
        
        communication = CommunicationRecord(
            instruction=instruction,
            readback=readback,
            timestamp=time.time(),
            response_time=response_time,
            score=assessment_result.score,
            errors=[e.to_dict() for e in assessment_result.errors]
        )
        
        self.current_session.add_communication(communication)
    
    def complete_session(self, assessment_result: AssessmentResult):
        """Complete the current session"""
        if not self.current_session:
            raise ValueError("No active session to complete.")
        
        # Calculate skill scores from assessment
        skill_scores = {
            "communication": assessment_result.phraseology_score,
            "readback_accuracy": assessment_result.readback_score,
            "overall": assessment_result.score
        }
        
        self.current_session.complete_session(
            assessment_result.score,
            skill_scores
        )
        
        # Update pilot progress
        pilot_id = self.current_session.pilot_id
        if pilot_id:
            if pilot_id not in self.pilot_progress:
                self.pilot_progress[pilot_id] = PilotProgress(pilot_id=pilot_id)
            
            self.pilot_progress[pilot_id].update_with_session(self.current_session)
        
        # Save session
        self._save_session(self.current_session)
        
        # Save pilot progress
        if pilot_id:
            self._save_pilot_progress(pilot_id)
        
        session_id = self.current_session.session_id
        self.current_session = None
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[TrainingSession]:
        """Get a session by ID"""
        session_file = os.path.join(self.data_dir, f"session_{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return TrainingSession.from_dict(data)
        return None
    
    def get_pilot_sessions(self, pilot_id: str, limit: int = 50) -> List[TrainingSession]:
        """Get recent sessions for a pilot"""
        if pilot_id not in self.pilot_progress:
            return []
        
        sessions = []
        for session_id in reversed(self.pilot_progress[pilot_id].session_history[-limit:]):
            session = self.get_session(session_id)
            if session:
                sessions.append(session)
        
        return sessions
    
    def get_pilot_progress(self, pilot_id: str) -> Optional[PilotProgress]:
        """Get progress for a pilot"""
        return self.pilot_progress.get(pilot_id)
    
    def get_performance_metrics(self, pilot_id: str, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for a pilot over specified days"""
        if pilot_id not in self.pilot_progress:
            return {}
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        sessions = self.get_pilot_sessions(pilot_id, limit=100)
        
        recent_sessions = [
            s for s in sessions 
            if s.start_time >= cutoff_time and s.status == SessionStatus.COMPLETED
        ]
        
        if not recent_sessions:
            return {
                "sessions_count": 0,
                "average_score": 0.0,
                "total_communications": 0,
                "improvement_trend": []
            }
        
        scores = [s.overall_score for s in recent_sessions]
        total_communications = sum(s.get_communication_count() for s in recent_sessions)
        
        # Calculate improvement trend (comparing first half to second half)
        if len(scores) >= 4:
            mid = len(scores) // 2
            first_half_avg = sum(scores[:mid]) / mid
            second_half_avg = sum(scores[mid:]) / (len(scores) - mid)
            improvement = second_half_avg - first_half_avg
        else:
            improvement = 0.0
        
        return {
            "sessions_count": len(recent_sessions),
            "average_score": sum(scores) / len(scores),
            "total_communications": total_communications,
            "improvement_trend": improvement,
            "best_score": max(scores),
            "worst_score": min(scores)
        }
    
    def get_skill_breakdown(self, pilot_id: str) -> Dict[str, Any]:
        """Get skill breakdown for a pilot"""
        if pilot_id not in self.pilot_progress:
            return {}
        
        progress = self.pilot_progress[pilot_id]
        
        return {
            skill_name: {
                "level": skill_progress.current_level,
                "average_score": skill_progress.average_score,
                "sessions": skill_progress.sessions_completed,
                "trend": skill_progress.trend[-10:] if skill_progress.trend else [],
                "weak_areas": skill_progress.weak_areas,
                "strong_areas": skill_progress.strong_areas
            }
            for skill_name, skill_progress in progress.skill_progress.items()
        }
    
    def _save_session(self, session: TrainingSession):
        """Save a session to disk"""
        session_file = os.path.join(self.data_dir, f"session_{session.session_id}.json")
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2)
        self._update_session_index()

    def _update_session_index(self):
        """Update index.json with session_id, pilot_id, scenario_id, start_time for all session files."""
        index_path = os.path.join(self.data_dir, "index.json")
        entries = []
        if not os.path.exists(self.data_dir):
            return
        for filename in os.listdir(self.data_dir):
            if not filename.startswith("session_") or not filename.endswith(".json"):
                continue
            path = os.path.join(self.data_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                entries.append({
                    "session_id": data.get("session_id"),
                    "pilot_id": data.get("pilot_id"),
                    "scenario_id": data.get("scenario_id"),
                    "start_time": data.get("start_time"),
                })
            except Exception:
                continue
        entries.sort(key=lambda e: (e.get("start_time") or 0), reverse=True)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump({"sessions": entries}, f, indent=2)
    
    def _save_pilot_progress(self, pilot_id: str):
        """Save pilot progress to disk"""
        if pilot_id not in self.pilot_progress:
            return
        
        progress_file = os.path.join(self.data_dir, f"pilot_{pilot_id}.json")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.pilot_progress[pilot_id].to_dict(), f, indent=2)
    
    def _load_pilot_progress(self):
        """Load all pilot progress from disk"""
        if not os.path.exists(self.data_dir):
            return
        
        for filename in os.listdir(self.data_dir):
            if filename.startswith("pilot_") and filename.endswith(".json"):
                pilot_id = filename[6:-5]  # Remove "pilot_" prefix and ".json" suffix
                progress_file = os.path.join(self.data_dir, filename)
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.pilot_progress[pilot_id] = PilotProgress.from_dict(data)
                except Exception as e:
                    logger.warning("Error loading progress for pilot %s: %s", pilot_id, e)

