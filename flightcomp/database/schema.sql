-- Database Schema for Pilot Training Application
-- SQLite Database Schema

-- Training Sessions Table
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
);

-- Communications Table
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
);

-- Pilot Progress Table
CREATE TABLE IF NOT EXISTS pilot_progress (
    pilot_id TEXT PRIMARY KEY,
    total_sessions INTEGER,
    total_communications INTEGER,
    overall_average_score REAL,
    session_history TEXT,
    last_training_date REAL,
    certifications TEXT
);

-- Skill Progress Table
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
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_sessions_pilot ON training_sessions(pilot_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON training_sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_communications_session ON communications(session_id);
CREATE INDEX IF NOT EXISTS idx_skills_pilot ON skill_progress(pilot_id);

