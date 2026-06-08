#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Alert Manager Module

Manages alerts for motion detection, camera offline events, and other security events.
"""

import time
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class AlertType(Enum):
    """Types of alerts."""
    MOTION_DETECTED = "motion_detected"
    CAMERA_OFFLINE = "camera_offline"
    CAMERA_ONLINE = "camera_online"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    SYSTEM_ERROR = "system_error"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Represents a single alert."""
    
    def __init__(self, 
                 alert_type: AlertType,
                 message: str,
                 camera_id: Optional[str] = None,
                 level: AlertLevel = AlertLevel.INFO,
                 data: Optional[Dict] = None):
        """
        Initialize an alert.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            camera_id: Associated camera ID (if applicable)
            level: Alert severity level
            data: Additional alert data
        """
        self.alert_type = alert_type
        self.message = message
        self.camera_id = camera_id
        self.level = level
        self.data = data or {}
        self.timestamp = datetime.now()
        self.acknowledged = False
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary."""
        return {
            'type': self.alert_type.value,
            'message': self.message,
            'camera_id': self.camera_id,
            'level': self.level.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Alert':
        """Create alert from dictionary."""
        alert = cls(
            alert_type=AlertType(data['type']),
            message=data['message'],
            camera_id=data.get('camera_id'),
            level=AlertLevel(data.get('level', 'info')),
            data=data.get('data', {})
        )
        alert.timestamp = datetime.fromisoformat(data['timestamp'])
        alert.acknowledged = data.get('acknowledged', False)
        return alert


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, 
                 log_file: Optional[str] = None,
                 max_alerts: int = 1000,
                 enable_sound: bool = True,
                 enable_visual: bool = True):
        """
        Initialize alert manager.
        
        Args:
            log_file: Path to alert log file (JSON)
            max_alerts: Maximum number of alerts to keep in memory
            enable_sound: Enable sound alerts
            enable_visual: Enable visual alerts
        """
        self.log_file = Path(log_file) if log_file else None
        self.max_alerts = max_alerts
        self.enable_sound = enable_sound
        self.enable_visual = enable_visual
        
        self.logger = logging.getLogger("the_eyes.alert_manager")
        
        # Alert storage
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        
        # Alert filters (suppress certain alerts)
        self.suppressed_alerts: Dict[AlertType, float] = {}  # {alert_type: suppress_until_timestamp}
        
        # Statistics
        self.alert_counts: Dict[AlertType, int] = {alert_type: 0 for alert_type in AlertType}
        
        # Load previous alerts if log file exists
        if self.log_file and self.log_file.exists():
            self._load_alerts()
    
    def add_alert(self, 
                  alert_type: AlertType,
                  message: str,
                  camera_id: Optional[str] = None,
                  level: AlertLevel = AlertLevel.INFO,
                  data: Optional[Dict] = None,
                  suppress_duplicates_seconds: float = 0.0) -> Alert:
        """
        Add a new alert.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            camera_id: Associated camera ID
            level: Alert severity level
            data: Additional alert data
            suppress_duplicates_seconds: Suppress duplicate alerts for this many seconds
            
        Returns:
            Created alert object
        """
        # Check if this alert type is suppressed
        if alert_type in self.suppressed_alerts:
            if time.time() < self.suppressed_alerts[alert_type]:
                return None
        
        # Create alert
        alert = Alert(alert_type, message, camera_id, level, data)
        
        # Add to alerts list
        self.alerts.append(alert)
        
        # Limit alert history
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Update statistics
        self.alert_counts[alert_type] = self.alert_counts.get(alert_type, 0) + 1
        
        # Suppress duplicates if requested
        if suppress_duplicates_seconds > 0:
            self.suppressed_alerts[alert_type] = time.time() + suppress_duplicates_seconds
        
        # Log alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }.get(level, logging.INFO)
        
        self.logger.log(log_level, f"Alert [{alert_type.value}]: {message} (Camera: {camera_id})")
        
        # Save to log file
        if self.log_file:
            self._save_alerts()
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
        
        # Trigger sound/visual alerts based on level
        if level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
            if self.enable_sound:
                self._play_alert_sound(level)
            if self.enable_visual:
                self._show_visual_alert(alert)
        
        return alert
    
    def add_alert_callback(self, callback: Callable):
        """
        Add a callback function to be called when an alert is created.
        
        Args:
            callback: Function that takes an Alert object as argument
        """
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable):
        """Remove an alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    def get_alerts(self, 
                   alert_type: Optional[AlertType] = None,
                   camera_id: Optional[str] = None,
                   level: Optional[AlertLevel] = None,
                   unacknowledged_only: bool = False,
                   limit: Optional[int] = None) -> List[Alert]:
        """
        Get alerts matching criteria.
        
        Args:
            alert_type: Filter by alert type
            camera_id: Filter by camera ID
            level: Filter by alert level
            unacknowledged_only: Only return unacknowledged alerts
            limit: Maximum number of alerts to return
            
        Returns:
            List of matching alerts
        """
        alerts = self.alerts
        
        # Apply filters
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        if camera_id:
            alerts = [a for a in alerts if a.camera_id == camera_id]
        if level:
            alerts = [a for a in alerts if a.level == level]
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            alerts = alerts[:limit]
        
        return alerts
    
    def acknowledge_alert(self, alert: Alert):
        """Mark an alert as acknowledged."""
        alert.acknowledged = True
        if self.log_file:
            self._save_alerts()
    
    def acknowledge_all(self, alert_type: Optional[AlertType] = None):
        """Acknowledge all alerts (optionally filtered by type)."""
        for alert in self.alerts:
            if alert_type is None or alert.alert_type == alert_type:
                alert.acknowledged = True
        if self.log_file:
            self._save_alerts()
    
    def clear_alerts(self, alert_type: Optional[AlertType] = None):
        """Clear alerts (optionally filtered by type)."""
        if alert_type:
            self.alerts = [a for a in self.alerts if a.alert_type != alert_type]
        else:
            self.alerts.clear()
        if self.log_file:
            self._save_alerts()
    
    def get_statistics(self) -> Dict:
        """Get alert statistics."""
        return {
            'total_alerts': len(self.alerts),
            'unacknowledged': sum(1 for a in self.alerts if not a.acknowledged),
            'by_type': {k.value: v for k, v in self.alert_counts.items()},
            'by_level': {
                level.value: sum(1 for a in self.alerts if a.level == level)
                for level in AlertLevel
            }
        }
    
    def _save_alerts(self):
        """Save alerts to log file."""
        try:
            if self.log_file:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_file, 'w') as f:
                    json.dump([a.to_dict() for a in self.alerts], f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving alerts: {e}")
    
    def _load_alerts(self):
        """Load alerts from log file."""
        try:
            if self.log_file and self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.alerts = [Alert.from_dict(a) for a in data]
                self.logger.info(f"Loaded {len(self.alerts)} alerts from {self.log_file}")
        except Exception as e:
            self.logger.error(f"Error loading alerts: {e}")
    
    def _play_alert_sound(self, level: AlertLevel):
        """Play alert sound (platform-specific)."""
        # Placeholder for sound alerts
        # Could use winsound on Windows, pygame, or other libraries
        try:
            import winsound
            if level == AlertLevel.CRITICAL:
                winsound.Beep(1000, 500)  # Higher frequency, longer duration
            elif level == AlertLevel.ERROR:
                winsound.Beep(800, 300)
        except ImportError:
            # Not on Windows or winsound not available
            pass
        except Exception as e:
            self.logger.debug(f"Could not play alert sound: {e}")
    
    def _show_visual_alert(self, alert: Alert):
        """Show visual alert (could be integrated with GUI)."""
        # This would typically trigger a GUI notification
        # For now, just log it
        self.logger.info(f"Visual alert: {alert.message}")

