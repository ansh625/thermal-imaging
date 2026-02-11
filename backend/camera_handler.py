import cv2
import asyncio
import logging
from typing import Dict, Optional
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraSession:
    def __init__(self, session_id: str, url: str, camera_id: int):
        self.session_id = session_id
        self.url = url
        self.camera_id = camera_id
        self.capture = None
        self.is_running = False
        self.last_frame = None
        self.fps = 25
        self.connected = False
        
    async def connect(self):
        try:
            if isinstance(self.url, int) or self.url.isdigit():
                camera_idx = int(self.url)
                self.capture = cv2.VideoCapture(camera_idx)
            elif self.url.lower().startswith('rtsp://'):
                self.capture = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            else:
                self.capture = cv2.VideoCapture(self.url)
            
            if not self.capture.isOpened():
                raise Exception("Failed to open camera")
            
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            self.fps = fps if fps > 0 else 25
            
            self.connected = True
            self.is_running = True
            logger.info(f"Camera {self.camera_id} connected: {self.url}")
            return True
        except Exception as e:
            logger.error(f"Camera connection error: {e}")
            return False
    
    async def get_frame(self):
        if not self.capture or not self.capture.isOpened():
            return None
        ret, frame = self.capture.read()
        if ret and frame is not None:
            self.last_frame = frame
            return frame
        return None
    
    async def disconnect(self):
        self.is_running = False
        if self.capture:
            self.capture.release()
        self.connected = False
        logger.info(f"Camera {self.camera_id} disconnected")

class CameraManager:
    def __init__(self):
        self.sessions: Dict[str, CameraSession] = {}
    
    def parse_camera_url(self, user_input: str):
        user_input = user_input.strip()
        if user_input.isdigit():
            return [int(user_input)]
        if user_input.lower().startswith(('rtsp://', 'http://', 'https://')):
            return [user_input]
        if self._is_ip_address(user_input):
            return self._generate_ip_urls(user_input)
        return [user_input]
    
    def _is_ip_address(self, text: str) -> bool:
        parts = text.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False
    
    def _generate_ip_urls(self, ip: str):
        urls = []
        for path in ['/video.mjpg', '/mjpg/video.mjpg', '/stream']:
            urls.append(f'http://{ip}{path}')
        for path in ['/live.sdp', '/stream1']:
            urls.append(f'rtsp://{ip}{path}')
        return urls
    
    async def create_session(self, session_id: str, url: str, camera_id: int):
        session = CameraSession(session_id, url, camera_id)
        connected = await session.connect()
        if connected:
            self.sessions[session_id] = session
            return session
        return None
    
    def get_session(self, session_id: str):
        return self.sessions.get(session_id)
    
    async def disconnect_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            await session.disconnect()
            del self.sessions[session_id]

camera_manager = CameraManager()