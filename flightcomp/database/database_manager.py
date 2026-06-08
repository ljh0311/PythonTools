"""
Database Manager for Pilot Training
Provides SQLite database integration for training records.

DEPRECATED: The application uses JSON files in data/training_records/ as the
source of truth (see utils/progress_tracker.py and data/README.md).
This module is kept for optional export or future use. Do not rely on
data/training.db for normal operation.
"""

import sqlite3
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from contextlib import contextmanager
from models.training_record import TrainingSession, CommunicationRecord, SessionStatus
from models.training_record import PilotProgress, SkillProgress
from utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages SQLite database for training records (deprecated; app uses JSON)."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager

        DEPRECATED: Prefer ProgressTracker and data/training_records/ JSON files.

        Args:
            db_path: Path to SQLite database file. Defaults to data/training.db
        """
        if db_path is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(current_dir, "data", "training.db")
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Training sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_sessions (
                    session_id TEXT PRIMARY KEY,
                    pilot_id TEXT,
                    scenario_id TEXT,
                    airport_icao TEXT,
                    difficulty TEXT,
                    start_time REAL,
                    end_time REAL,
                    status TEXT,
                    overall_score REAL,
                    skill_scores TEXT,
                    metadata TEXT
                )
            """)
            
            # Communications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS communications (
                    communication_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    instruction TEXT,
                    readback TEXT,
                    timestamp REAL,
                    response_time REAL,
                    score REAL,
                    errors TEXT,
                    FOREIGN KEY (session_id) REFERENCES training_sessions(session_id)
                )
            """)
            
            # Pilot progress table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pilot_progress (
                    pilot_id TEXT PRIMARY KEY,
                    total_sessions INTEGER,
                    total_communications INTEGER,
                    overall_average_score REAL,
                    session_history TEXT,
                    last_training_date REAL,
                    certifications TEXT
                )
            """)
            
            # Skill progress table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_progress (
                    skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pilot_id TEXT,
                    skill_name TEXT,
                    current_level TEXT,
                    sessions_completed INTEGER,
                    average_score REAL,
                    trend TEXT,
                    last_practiced REAL,
                    weak_areas TEXT,
                    strong_areas TEXT,
                    FOREIGN KEY (pilot_id) REFERENCES pilot_progress(pilot_id),
                    UNIQUE(pilot_id, skill_name)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_pilot 
                ON training_sessions(pilot_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time 
                ON training_sessions(start_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_communications_session 
                ON communications(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_skills_pilot 
                ON skill_progress(pilot_id)
            """)
    
    def save_session(self, session: TrainingSession):
        """Save training session to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO training_sessions
                (session_id, pilot_id, scenario_id, airport_icao, difficulty,
                 start_time, end_time, status, overall_score, skill_scores, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.pilot_id,
                session.scenario_id,
                session.airport_icao,
                session.difficulty,
                session.start_time,
                session.end_time,
                session.status.value,
                session.overall_score,
                json.dumps(session.skill_scores),
                json.dumps(session.metadata)
            ))
            
            # Save communications
            for comm in session.communications:
                cursor.execute("""
                    INSERT INTO communications
                    (session_id, instruction, readback, timestamp, response_time, score, errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id,
                    comm.instruction,
                    comm.readback,
                    comm.timestamp,
                    comm.response_time,
                    comm.score,
                    json.dumps(comm.errors)
                ))
    
    def get_session(self, session_id: str) -> Optional[TrainingSession]:
        """Get training session from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM training_sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Load communications
            cursor.execute("""
                SELECT * FROM communications WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            
            communications = []
            for comm_row in cursor.fetchall():
                communications.append(CommunicationRecord(
                    instruction=comm_row["instruction"],
                    readback=comm_row["readback"],
                    timestamp=comm_row["timestamp"],
                    response_time=comm_row["response_time"],
                    score=comm_row["score"],
                    errors=json.loads(comm_row["errors"] or "[]")
                ))
            
            return TrainingSession(
                session_id=row["session_id"],
                pilot_id=row["pilot_id"],
                scenario_id=row["scenario_id"],
                airport_icao=row["airport_icao"],
                difficulty=row["difficulty"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                status=SessionStatus(row["status"]),
                communications=communications,
                overall_score=row["overall_score"],
                skill_scores=json.loads(row["skill_scores"] or "{}"),
                metadata=json.loads(row["metadata"] or "{}")
            )
    
    def get_pilot_sessions(self, pilot_id: str, limit: int = 50) -> List[TrainingSession]:
        """Get recent sessions for a pilot"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id FROM training_sessions
                WHERE pilot_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            """, (pilot_id, limit))
            
            session_ids = [row["session_id"] for row in cursor.fetchall()]
            sessions = []
            for session_id in session_ids:
                session = self.get_session(session_id)
                if session:
                    sessions.append(session)
            
            return sessions
    
    def save_pilot_progress(self, progress: PilotProgress):
        """Save pilot progress to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Save main progress
            cursor.execute("""
                INSERT OR REPLACE INTO pilot_progress
                (pilot_id, total_sessions, total_communications, overall_average_score,
                 session_history, last_training_date, certifications)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                progress.pilot_id,
                progress.total_sessions,
                progress.total_communications,
                progress.overall_average_score,
                json.dumps(progress.session_history),
                progress.last_training_date,
                json.dumps(progress.certifications)
            ))
            
            # Save skill progress
            for skill_name, skill_progress in progress.skill_progress.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO skill_progress
                    (pilot_id, skill_name, current_level, sessions_completed,
                     average_score, trend, last_practiced, weak_areas, strong_areas)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    progress.pilot_id,
                    skill_progress.skill_name,
                    skill_progress.current_level,
                    skill_progress.sessions_completed,
                    skill_progress.average_score,
                    json.dumps(skill_progress.trend),
                    skill_progress.last_practiced,
                    json.dumps(skill_progress.weak_areas),
                    json.dumps(skill_progress.strong_areas)
                ))
    
    def get_pilot_progress(self, pilot_id: str) -> Optional[PilotProgress]:
        """Get pilot progress from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM pilot_progress WHERE pilot_id = ?
            """, (pilot_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Load skill progress
            cursor.execute("""
                SELECT * FROM skill_progress WHERE pilot_id = ?
            """, (pilot_id,))
            
            skill_progress = {}
            for skill_row in cursor.fetchall():
                skill = SkillProgress(
                    skill_name=skill_row["skill_name"],
                    current_level=skill_row["current_level"],
                    sessions_completed=skill_row["sessions_completed"],
                    average_score=skill_row["average_score"],
                    trend=json.loads(skill_row["trend"] or "[]"),
                    last_practiced=skill_row["last_practiced"],
                    weak_areas=json.loads(skill_row["weak_areas"] or "[]"),
                    strong_areas=json.loads(skill_row["strong_areas"] or "[]")
                )
                skill_progress[skill.skill_name] = skill
            
            return PilotProgress(
                pilot_id=row["pilot_id"],
                total_sessions=row["total_sessions"],
                total_communications=row["total_communications"],
                overall_average_score=row["overall_average_score"],
                skill_progress=skill_progress,
                session_history=json.loads(row["session_history"] or "[]"),
                last_training_date=row["last_training_date"],
                certifications=json.loads(row["certifications"] or "[]")
            )
    
    def get_statistics(self, pilot_id: Optional[str] = None) -> Dict[str, Any]:
        """Get training statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            if pilot_id:
                # Pilot-specific statistics
                cursor.execute("""
                    SELECT COUNT(*) as total_sessions,
                           AVG(overall_score) as avg_score,
                           MIN(overall_score) as min_score,
                           MAX(overall_score) as max_score
                    FROM training_sessions
                    WHERE pilot_id = ?
                """, (pilot_id,))
            else:
                # Global statistics
                cursor.execute("""
                    SELECT COUNT(*) as total_sessions,
                           AVG(overall_score) as avg_score,
                           MIN(overall_score) as min_score,
                           MAX(overall_score) as max_score
                    FROM training_sessions
                """)
            
            row = cursor.fetchone()
            stats["sessions"] = {
                "total": row["total_sessions"] or 0,
                "average_score": row["avg_score"] or 0.0,
                "min_score": row["min_score"] or 0.0,
                "max_score": row["max_score"] or 0.0
            }
            
            # Communication statistics
            if pilot_id:
                cursor.execute("""
                    SELECT COUNT(*) as total_communications,
                           AVG(score) as avg_score,
                           AVG(response_time) as avg_response_time
                    FROM communications c
                    JOIN training_sessions s ON c.session_id = s.session_id
                    WHERE s.pilot_id = ?
                """, (pilot_id,))
            else:
                cursor.execute("""
                    SELECT COUNT(*) as total_communications,
                           AVG(score) as avg_score,
                           AVG(response_time) as avg_response_time
                    FROM communications
                """)
            
            row = cursor.fetchone()
            stats["communications"] = {
                "total": row["total_communications"] or 0,
                "average_score": row["avg_score"] or 0.0,
                "average_response_time": row["avg_response_time"] or 0.0
            }
            
            return stats
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            logger.warning("Error backing up database: %s", e)
            return False
    
    def export_data(self, pilot_id: str, output_path: str) -> bool:
        """Export pilot data to JSON file"""
        try:
            progress = self.get_pilot_progress(pilot_id)
            sessions = self.get_pilot_sessions(pilot_id, limit=1000)
            
            export_data = {
                "pilot_id": pilot_id,
                "progress": progress.to_dict() if progress else None,
                "sessions": [s.to_dict() for s in sessions]
            }
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.warning("Error exporting data: %s", e)
            return False

