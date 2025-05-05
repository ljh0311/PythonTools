import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple

class VideoProcessor:
    """Class for extracting and processing frames from video input."""
    
    def __init__(self, video_path: str):
        """Initialize the video processor.
        
        Args:
            video_path (str): Path to the input video file
        """
        self.video_path = Path(video_path)
        self.cap = None
        
    def extract_frames(self, output_dir: str, frame_interval: int = 1) -> List[str]:
        """Extract frames from the video at specified intervals.
        
        Args:
            output_dir (str): Directory to save extracted frames
            frame_interval (int): Extract every nth frame
            
        Returns:
            List[str]: Paths to extracted frames
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        frame_paths = []
        self.cap = cv2.VideoCapture(str(self.video_path))
        
        frame_count = 0
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                frame_path = output_dir / f"frame_{frame_count:06d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                frame_paths.append(str(frame_path))
                
            frame_count += 1
            
        self.cap.release()
        return frame_paths
    
    def get_video_info(self) -> Tuple[int, int, int, float]:
        """Get basic information about the video.
        
        Returns:
            Tuple containing:
            - Width (int)
            - Height (int)
            - Total frames (int)
            - FPS (float)
        """
        self.cap = cv2.VideoCapture(str(self.video_path))
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.cap.release()
        
        return width, height, total_frames, fps 