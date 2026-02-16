import cv2
import os
from datetime import datetime
from typing import Optional
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecordingManager:
    def __init__(self, output_dir: str = "recordings"):
        self.output_dir = output_dir
        self.active_recordings = {}  # session_id -> VideoWriter
        Path(output_dir).mkdir(exist_ok=True)
    
    def start_recording(self, session_id: str, fps: float, 
                       frame_size: tuple, camera_name: str = "camera") -> Optional[str]:
        """Start recording for a session"""
        if session_id in self.active_recordings:
            logger.warning(f"Recording already active for {session_id}")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{camera_name}_{timestamp}.mp4"
            filepath = os.path.join(self.output_dir, filename)
            
            # Use H264 codec for MP4
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(filepath, fourcc, fps, frame_size)
            
            if not writer.isOpened():
                logger.error(f"Failed to open video writer for {filepath}")
                return None
            
            self.active_recordings[session_id] = {
                'writer': writer,
                'filepath': filepath,
                'filename': filename,
                'start_time': datetime.now(),
                'frame_count': 0
            }
            
            logger.info(f"Recording started: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return None
    
    def write_frame(self, session_id: str, frame):
        """Write a frame to the recording"""
        if session_id not in self.active_recordings:
            return False
        
        try:
            recording = self.active_recordings[session_id]
            recording['writer'].write(frame)
            recording['frame_count'] += 1
            return True
        except Exception as e:
            logger.error(f"Error writing frame: {e}")
            return False
    
    def stop_recording(self, session_id: str) -> Optional[dict]:
        """Stop recording and return stats"""
        if session_id not in self.active_recordings:
            return None
        
        try:
            recording = self.active_recordings[session_id]
            recording['writer'].release()
            
            end_time = datetime.now()
            duration = (end_time - recording['start_time']).total_seconds()
            
            # Get file size
            file_size = os.path.getsize(recording['filepath']) if os.path.exists(recording['filepath']) else 0
            
            stats = {
                'filepath': recording['filepath'],
                'filename': recording['filename'],
                'duration_seconds': int(duration),
                'file_size_bytes': file_size,
                'frame_count': recording['frame_count'],
                'started_at': recording['start_time'],
                'ended_at': end_time
            }
            
            del self.active_recordings[session_id]
            logger.info(f"Recording stopped: {recording['filename']} ({duration:.1f}s)")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return None
    
    def is_recording(self, session_id: str) -> bool:
        """Check if session is recording"""
        return session_id in self.active_recordings
    
    def get_active_recordings(self) -> list:
        """Get list of active recording sessions"""
        return list(self.active_recordings.keys())

# Global instance
recording_manager = RecordingManager()