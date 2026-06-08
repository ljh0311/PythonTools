#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Video Recording Module

Provides video recording capabilities with motion-triggered and continuous recording.
"""

import cv2
import os
import time
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime
import threading


class VideoRecorder:
    """Video recorder for camera feeds."""
    
    def __init__(self, 
                 output_dir: str = "recordings",
                 codec: str = "mp4v",
                 fps: float = 30.0,
                 quality: int = 1,
                 max_file_size_mb: int = 500,
                 max_duration_minutes: int = 60):
        """
        Initialize video recorder.
        
        Args:
            output_dir: Directory to save recordings
            codec: Video codec (mp4v, XVID, H264, etc.)
            fps: Frames per second for recording
            quality: Quality level (1-10, higher = better quality)
            max_file_size_mb: Maximum file size in MB before splitting
            max_duration_minutes: Maximum duration in minutes before splitting
        """
        self.output_dir = Path(output_dir)
        self.codec = codec
        self.fps = fps
        self.quality = quality
        self.max_file_size_mb = max_file_size_mb
        self.max_duration_minutes = max_duration_minutes
        
        self.logger = logging.getLogger("the_eyes.recorder")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Active recordings: {camera_id: writer_info}
        self.active_recordings: Dict[str, Dict] = {}
        # RLock: write_frame may call stop/start_recording while already holding the lock.
        self.recording_lock = threading.RLock()
        
        # Recording statistics
        self.recording_stats: Dict[str, Dict] = {}
        
    def start_recording(self, 
                       camera_id: str,
                       width: int,
                       height: int,
                       motion_triggered: bool = False) -> bool:
        """
        Start recording for a camera.
        
        Args:
            camera_id: Camera identifier
            width: Video width
            height: Video height
            motion_triggered: Whether this is motion-triggered recording
            
        Returns:
            True if recording started successfully
        """
        with self.recording_lock:
            if camera_id in self.active_recordings:
                self.logger.warning(f"Recording already active for camera {camera_id}")
                return False
            
            try:
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                prefix = "motion" if motion_triggered else "continuous"
                filename = f"{prefix}_{camera_id}_{timestamp}.mp4"
                filepath = self.output_dir / filename
                
                # Get codec
                fourcc = cv2.VideoWriter_fourcc(*self.codec)
                
                # Create video writer
                writer = cv2.VideoWriter(
                    str(filepath),
                    fourcc,
                    self.fps,
                    (width, height)
                )
                
                if not writer.isOpened():
                    self.logger.error(f"Failed to open video writer for {filepath}")
                    return False
                
                # Store recording info
                self.active_recordings[camera_id] = {
                    'writer': writer,
                    'filepath': filepath,
                    'start_time': time.time(),
                    'frame_count': 0,
                    'motion_triggered': motion_triggered,
                    'width': width,
                    'height': height
                }
                
                # Initialize stats
                if camera_id not in self.recording_stats:
                    self.recording_stats[camera_id] = {
                        'total_recordings': 0,
                        'total_duration': 0.0,
                        'total_size_mb': 0.0
                    }
                
                self.logger.info(f"Started {'motion-triggered' if motion_triggered else 'continuous'} "
                               f"recording for camera {camera_id}: {filepath}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error starting recording for camera {camera_id}: {e}")
                return False
    
    def stop_recording(self, camera_id: str) -> Optional[Path]:
        """
        Stop recording for a camera.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Path to recorded file, or None if error
        """
        with self.recording_lock:
            if camera_id not in self.active_recordings:
                self.logger.warning(f"No active recording for camera {camera_id}")
                return None
            
            try:
                recording_info = self.active_recordings[camera_id]
                writer = recording_info['writer']
                filepath = recording_info['filepath']
                start_time = recording_info['start_time']
                frame_count = recording_info['frame_count']
                
                # Release writer
                writer.release()
                
                # Calculate duration and file size
                duration = time.time() - start_time
                file_size_mb = filepath.stat().st_size / (1024 * 1024)
                
                # Update statistics
                if camera_id in self.recording_stats:
                    stats = self.recording_stats[camera_id]
                    stats['total_recordings'] += 1
                    stats['total_duration'] += duration
                    stats['total_size_mb'] += file_size_mb
                
                # Remove from active recordings
                del self.active_recordings[camera_id]
                
                self.logger.info(f"Stopped recording for camera {camera_id}: {filepath} "
                               f"({duration:.1f}s, {file_size_mb:.2f} MB, {frame_count} frames)")
                
                return filepath
                
            except Exception as e:
                self.logger.error(f"Error stopping recording for camera {camera_id}: {e}")
                if camera_id in self.active_recordings:
                    del self.active_recordings[camera_id]
                return None
    
    def write_frame(self, camera_id: str, frame) -> bool:
        """
        Write a frame to the active recording.
        
        Args:
            camera_id: Camera identifier
            frame: Frame to write (numpy array)
            
        Returns:
            True if frame was written successfully
        """
        with self.recording_lock:
            if camera_id not in self.active_recordings:
                return False
            
            try:
                recording_info = self.active_recordings[camera_id]
                writer = recording_info['writer']
                
                # Check if we need to split the file
                current_time = time.time()
                duration = current_time - recording_info['start_time']
                filepath = recording_info['filepath']
                
                # Check duration limit
                if duration >= self.max_duration_minutes * 60:
                    self.logger.info(f"Reached duration limit for camera {camera_id}, splitting file")
                    self.stop_recording(camera_id)
                    # Start new recording
                    return self.start_recording(
                        camera_id,
                        recording_info['width'],
                        recording_info['height'],
                        recording_info['motion_triggered']
                    )
                
                # Check file size limit
                if filepath.exists():
                    file_size_mb = filepath.stat().st_size / (1024 * 1024)
                    if file_size_mb >= self.max_file_size_mb:
                        self.logger.info(f"Reached file size limit for camera {camera_id}, splitting file")
                        self.stop_recording(camera_id)
                        # Start new recording
                        return self.start_recording(
                            camera_id,
                            recording_info['width'],
                            recording_info['height'],
                            recording_info['motion_triggered']
                        )
                
                # Write frame
                writer.write(frame)
                recording_info['frame_count'] += 1
                
                return True
                
            except Exception as e:
                self.logger.error(f"Error writing frame for camera {camera_id}: {e}")
                return False
    
    def is_recording(self, camera_id: str) -> bool:
        """Check if a camera is currently recording."""
        with self.recording_lock:
            return camera_id in self.active_recordings
    
    def stop_all_recordings(self):
        """Stop all active recordings."""
        camera_ids = list(self.active_recordings.keys())
        for camera_id in camera_ids:
            self.stop_recording(camera_id)
    
    def get_statistics(self, camera_id: Optional[str] = None) -> Dict:
        """
        Get recording statistics.
        
        Args:
            camera_id: Specific camera ID, or None for all cameras
            
        Returns:
            Dictionary with statistics
        """
        if camera_id:
            return self.recording_stats.get(camera_id, {})
        return self.recording_stats.copy()
    
    def cleanup_old_recordings(self, days_to_keep: int = 30):
        """
        Delete recordings older than specified days.
        
        Args:
            days_to_keep: Number of days to keep recordings
        """
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for filepath in self.output_dir.glob("*.mp4"):
                if filepath.stat().st_mtime < cutoff_time:
                    filepath.unlink()
                    deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} old recordings (older than {days_to_keep} days)")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old recordings: {e}")
            return 0

