import cv2
import os
from datetime import datetime
from typing import Optional
import logging
from pathlib import Path
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecordingManager:
    def __init__(self, output_dir: str = "recordings"):
        self.output_dir = output_dir
        self.active_recordings = {}  # session_id -> VideoWriter
        Path(output_dir).mkdir(exist_ok=True)
        self.preferred_codec = self._get_preferred_codec()
    
    def _get_preferred_codec(self) -> str:
        """
        Get the best codec for the current platform.
        Prioritize H.264 for Windows compatibility, then H.265, then mp4v
        """
        system = platform.system()
        
        if system == "Windows":
            # H.264 is most compatible on Windows
            # Try in order: 'H264', 'h264', 'avc1', 'mp4v', 'DIVX'
            return 'H264'  # Will fallback if not available
        elif system == "Darwin":
            # macOS - use H.264
            return 'avc1'
        else:
            # Linux - use H.264
            return 'mp4v'
    
    def _get_video_writer(self, filepath: str, fourcc: int, fps: float, frame_size: tuple):
        """
        Create video writer with fallback codec support
        """
        writer = cv2.VideoWriter(filepath, fourcc, fps, frame_size)
        
        if not writer.isOpened():
            logger.warning(f"Failed to open writer with fourcc {fourcc}, trying alternative codecs")
            return None
        
        return writer
    
    def _select_codec(self, filepath: str, fps: float, frame_size: tuple) -> tuple:
        """
        Select the best available codec and try to create a working VideoWriter.
        Returns (fourcc_code, writer) or (None, None) if all fail
        """
        codec_options = [
            ('H264', 'H264'),
            ('mp4v', 'mp4v'),
            ('avc1', 'avc1'),
            ('DIVX', 'DIVX'),
        ]
        
        for codec_name, codec_code in codec_options:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec_code)
                writer = self._get_video_writer(filepath, fourcc, fps, frame_size)
                
                if writer is not None and writer.isOpened():
                    logger.info(f"Using codec: {codec_name} ({codec_code})")
                    return (fourcc, writer)
                
            except Exception as e:
                logger.debug(f"Codec {codec_name} not available: {e}")
                continue
        
        logger.error(f"No suitable video codec found on this system")
        return (None, None)
    
    def start_recording(self, session_id: str, fps: float, 
                       frame_size: tuple, camera_name: str = "camera") -> Optional[str]:
        """
        Start recording for a session with annotated frames.
        
        Args:
            session_id: Unique session identifier
            fps: Frames per second for the video
            frame_size: Tuple of (width, height) for the video
            camera_name: Name of the camera for filename
        
        Returns:
            Filepath if successful, None otherwise
        """
        if session_id in self.active_recordings:
            logger.warning(f"Recording already active for {session_id}")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{camera_name}_{timestamp}.mp4"
            filepath = os.path.join(self.output_dir, filename)
            
            # Ensure fps and frame size are valid
            fps = float(fps) if fps > 0 else 30
            frame_size = (int(frame_size[0]), int(frame_size[1]))
            
            # Select appropriate codec
            fourcc, writer = self._select_codec(filepath, fps, frame_size)
            
            if writer is None:
                logger.error(f"Failed to create video writer for {filepath}")
                return None
            
            self.active_recordings[session_id] = {
                'writer': writer,
                'filepath': filepath,
                'filename': filename,
                'start_time': datetime.now(),
                'frame_count': 0,
                'fps': fps,
                'frame_size': frame_size,
                'fourcc': fourcc
            }
            
            logger.info(f"Recording started: {filepath} (FPS: {fps}, Resolution: {frame_size})")
            return filepath
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return None
    
    def write_frame(self, session_id: str, frame, enforce_size: bool = True) -> bool:
        """
        Write a frame to the recording.
        
        Args:
            session_id: Session identifier
            frame: Frame to write (should have bounding boxes and labels already drawn)
            enforce_size: If True, resize frame to match expected size
        
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.active_recordings:
            return False
        
        try:
            recording = self.active_recordings[session_id]
            
            # Ensure frame size matches what VideoWriter expects
            if enforce_size:
                expected_size = recording['frame_size']
                if frame.shape[1] != expected_size[0] or frame.shape[0] != expected_size[1]:
                    frame = cv2.resize(frame, expected_size, interpolation=cv2.INTER_LINEAR)
            
            # Ensure frame is in BGR color space (OpenCV standard)
            if len(frame.shape) == 2:  # Grayscale
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:  # RGBA
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            
            recording['writer'].write(frame)
            recording['frame_count'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error writing frame: {e}")
            return False
    
    def stop_recording(self, session_id: str) -> Optional[dict]:
        """
        Stop recording and return statistics.
        
        Returns:
            Dictionary with recording info or None if session not found
        """
        if session_id not in self.active_recordings:
            return None
        
        try:
            recording = self.active_recordings[session_id]
            writer = recording['writer']
            
            # Properly release the video writer
            if writer is not None:
                writer.release()
            
            end_time = datetime.now()
            duration = (end_time - recording['start_time']).total_seconds()
            
            # Verify file exists and get size
            filepath = recording['filepath']
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            
            # Verify the file is valid and readable
            if file_size > 0:
                try:
                    test_reader = cv2.VideoCapture(filepath)
                    if test_reader.isOpened():
                        frame_count_cv = int(test_reader.get(cv2.CAP_PROP_FRAME_COUNT))
                        logger.info(f"MP4 validation: File is playable, {frame_count_cv} frames")
                        test_reader.release()
                    else:
                        logger.warning(f"File may not be readable: {filepath}")
                except Exception as e:
                    logger.warning(f"Could not validate MP4: {e}")
            
            stats = {
                'filepath': filepath,
                'filename': recording['filename'],
                'duration_seconds': duration,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'frame_count': recording['frame_count'],
                'expected_fps': recording['fps'],
                'resolution': f"{recording['frame_size'][0]}x{recording['frame_size'][1]}",
                'started_at': recording['start_time'],
                'ended_at': end_time
            }
            
            del self.active_recordings[session_id]
            logger.info(f"Recording stopped: {recording['filename']} ({duration:.1f}s, {file_size / (1024*1024):.2f}MB)")
            
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
    
    def add_timestamp(self, frame, timestamp: Optional[str] = None):
        """
        Draw timestamp on frame for debugging/reference.
        Modifies frame in-place.
        
        Args:
            frame: The frame to annotate
            timestamp: Optional custom timestamp string. If None, uses current time.
        
        Returns:
            The frame with timestamp added
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add text with white color and black outline for visibility
        cv2.putText(
            frame,
            timestamp,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        return frame

# Global instance
recording_manager = RecordingManager()