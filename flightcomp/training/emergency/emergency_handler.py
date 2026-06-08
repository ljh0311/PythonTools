"""
Emergency Handler for Pilot Training
Manages emergency procedure execution and time-critical simulations
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from training.emergency.emergency_scenarios import (
    EmergencyScenario,
    EmergencyType,
    EmergencySeverity,
    EmergencyScenarioManager
)


class ActionStatus(Enum):
    """Status of an emergency action"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class EmergencyAction:
    """Represents an action in emergency procedure"""
    action_id: str
    description: str
    required: bool = True
    time_limit: Optional[float] = None  # seconds
    status: ActionStatus = ActionStatus.NOT_STARTED
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    notes: str = ""
    
    def start(self):
        """Mark action as started"""
        self.status = ActionStatus.IN_PROGRESS
        self.start_time = time.time()
    
    def complete(self, notes: str = ""):
        """Mark action as completed"""
        self.status = ActionStatus.COMPLETED
        self.completion_time = time.time()
        self.notes = notes
    
    def fail(self, reason: str = ""):
        """Mark action as failed"""
        self.status = ActionStatus.FAILED
        self.completion_time = time.time()
        self.notes = reason
    
    def check_timeout(self) -> bool:
        """Check if action has timed out"""
        if self.time_limit and self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > self.time_limit:
                self.status = ActionStatus.TIMEOUT
                return True
        return False


@dataclass
class EmergencySession:
    """Represents an active emergency training session"""
    session_id: str
    scenario: EmergencyScenario
    start_time: float
    actions: List[EmergencyAction] = field(default_factory=list)
    communications: List[str] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    success: bool = False
    failure_reason: Optional[str] = None
    
    def __post_init__(self):
        """Initialize actions from scenario"""
        for i, action_desc in enumerate(self.scenario.required_actions):
            action = EmergencyAction(
                action_id=f"action_{i}",
                description=action_desc,
                required=True
            )
            self.actions.append(action)
        
        # Initialize state from scenario
        self.current_state = self.scenario.initial_conditions.copy()
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start"""
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> Optional[float]:
        """Get remaining time if time-limited"""
        if self.scenario.time_limit_seconds:
            elapsed = self.get_elapsed_time()
            remaining = self.scenario.time_limit_seconds - elapsed
            return max(0, remaining)
        return None
    
    def is_time_critical(self) -> bool:
        """Check if scenario is time-critical"""
        return self.scenario.time_critical
    
    def check_success(self) -> bool:
        """Check if emergency was handled successfully"""
        # Check if all required actions completed
        required_actions = [a for a in self.actions if a.required]
        all_completed = all(a.status == ActionStatus.COMPLETED for a in required_actions)
        
        # Check time limit
        within_time = True
        if self.scenario.time_limit_seconds:
            within_time = self.get_elapsed_time() <= self.scenario.time_limit_seconds
        
        # Check failure conditions
        no_failures = True
        for condition in self.scenario.failure_conditions:
            # Simple check - in real implementation, would evaluate conditions
            if condition.lower() in str(self.failure_reason).lower():
                no_failures = False
                break
        
        return all_completed and within_time and no_failures
    
    def add_communication(self, message: str):
        """Add a communication to the session"""
        self.communications.append(f"[{time.time() - self.start_time:.1f}s] {message}")


class EmergencyHandler:
    """Handles emergency procedure training"""
    
    def __init__(self):
        """Initialize emergency handler"""
        self.scenario_manager = EmergencyScenarioManager()
        self.active_sessions: Dict[str, EmergencySession] = {}
        self.callbacks: Dict[str, Callable] = {}
    
    def start_emergency_session(self, emergency_id: str) -> Optional[str]:
        """
        Start a new emergency training session
        
        Returns:
            Session ID if successful, None otherwise
        """
        scenario = self.scenario_manager.get_scenario(emergency_id)
        if not scenario:
            return None
        
        session_id = f"emergency_{int(time.time())}"
        session = EmergencySession(
            session_id=session_id,
            scenario=scenario,
            start_time=time.time()
        )
        
        self.active_sessions[session_id] = session
        
        # Notify callback if registered
        if "session_started" in self.callbacks:
            self.callbacks["session_started"](session)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[EmergencySession]:
        """Get emergency session by ID"""
        return self.active_sessions.get(session_id)
    
    def execute_action(self, session_id: str, action_id: str) -> bool:
        """
        Execute an action in the emergency session
        
        Returns:
            True if action executed successfully
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        action = next((a for a in session.actions if a.action_id == action_id), None)
        if not action:
            return False
        
        if action.status == ActionStatus.NOT_STARTED:
            action.start()
        elif action.status == ActionStatus.IN_PROGRESS:
            action.complete()
            
            # Check if all actions completed
            if all(a.status in [ActionStatus.COMPLETED, ActionStatus.FAILED] 
                   for a in session.actions):
                session.completed = True
                session.success = session.check_success()
                
                if "session_completed" in self.callbacks:
                    self.callbacks["session_completed"](session)
        
        return True
    
    def add_communication(self, session_id: str, message: str):
        """Add communication to emergency session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        session.add_communication(message)
        
        # Check if communication matches expected
        expected = session.scenario.expected_communications
        if message and any(exp.lower() in message.lower() for exp in expected):
            # Communication matches expected pattern
            pass
    
    def check_time_limits(self):
        """Check time limits for all active sessions"""
        current_time = time.time()
        sessions_to_complete = []
        
        for session_id, session in self.active_sessions.items():
            if session.completed:
                continue
            
            # Check action timeouts
            for action in session.actions:
                if action.status == ActionStatus.IN_PROGRESS:
                    action.check_timeout()
            
            # Check session time limit
            if session.scenario.time_limit_seconds:
                elapsed = session.get_elapsed_time()
                if elapsed > session.scenario.time_limit_seconds:
                    session.completed = True
                    session.success = False
                    session.failure_reason = "Time limit exceeded"
                    sessions_to_complete.append(session_id)
        
        # Complete timed-out sessions
        for session_id in sessions_to_complete:
            session = self.active_sessions[session_id]
            if "session_completed" in self.callbacks:
                self.callbacks["session_completed"](session)
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for emergency events"""
        self.callbacks[event] = callback
    
    def end_session(self, session_id: str):
        """End an emergency session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.completed = True
            session.success = session.check_success()
            
            if "session_completed" in self.callbacks:
                self.callbacks["session_completed"](session)
            
            # Keep session for review, but mark as inactive
            # Could move to completed_sessions dict

