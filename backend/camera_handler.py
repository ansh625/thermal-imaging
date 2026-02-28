"""
Camera Handler - Handles camera connections and sessions
Supports USB, RTSP, IP, and RAW stream types
"""

import cv2
import asyncio
import logging
import time
from typing import Dict, Optional
from urllib.parse import urlparse, unquote
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraSession:
    def __init__(self, session_id: str, url, camera_id: int, stream_type: str = "rtsp"):
        self.session_id = session_id
        self.url = url
        self.camera_id = camera_id
        self.stream_type = stream_type or "rtsp"
        self.capture = None
        self.connected = False
        self.is_running = False
        self.last_frame = None
        self.fps = 25

    async def connect(self):
        """Stable camera connection with support for USB, RTSP, IP, and RAW streams"""
        try:
            logger.info(f"[Camera {self.camera_id}] Opening source: {self.url} (type: {self.stream_type})")

            source = self.url
            urls_to_try = [source]  # Primary URL

            # Handle different stream types
            if self.stream_type.lower() == "usb":
                # USB camera - use DirectShow on Windows
                if isinstance(source, str) and source.isdigit():
                    source = int(source)
                elif isinstance(source, str):
                    source = int(source) if source.isdigit() else 0
                
                self.capture = cv2.VideoCapture(source, cv2.CAP_DSHOW)
            
            elif self.stream_type.lower() == "rtsp":
                # RTSP or IP camera - use FFMPEG backend
                # If simple connection fails, try alternative paths
                source = unquote(source)
                urls_to_try = self._get_rtsp_url_variations(source)
                
                # Try each RTSP URL variation
                success = False
                last_error = None
                for rtsp_url in urls_to_try:
                    try:
                        logger.info(f"[Camera {self.camera_id}] Trying RTSP URL: {rtsp_url}")
                        test_capture = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                        
                        if test_capture and test_capture.isOpened():
                            # Try to read one frame to verify it's working
                            ret, frame = test_capture.read()
                            if ret and frame is not None:
                                self.capture = test_capture
                                self.url = rtsp_url  # Update URL to the working one
                                logger.info(f"[Camera {self.camera_id}] Successfully connected with URL: {rtsp_url}")
                                success = True
                                break
                            else:
                                test_capture.release()
                        else:
                            if test_capture:
                                test_capture.release()
                    except Exception as e:
                        last_error = str(e)
                        logger.debug(f"[Camera {self.camera_id}] Failed with URL {rtsp_url}: {e}")
                        continue
                
                if not success:
                    error_msg = f"Could not connect to RTSP stream. Tried: {', '.join(urls_to_try)}"
                    if last_error:
                        error_msg += f" (Last error: {last_error})"
                    raise Exception(error_msg)
            
            elif self.stream_type.lower() == "ip":
                # IP camera - use FFMPEG with HTTP
                source = unquote(source)
                parsed = urlparse(source)
                
                if parsed.scheme in ('rtsp', 'http', 'https'):
                    self.capture = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                else:
                    # Assume IP hostname, add http://
                    self.capture = cv2.VideoCapture(f"http://{source}", cv2.CAP_FFMPEG)
            
            elif self.stream_type.lower() == "raw":
                # RAW stream - try different backends
                source = unquote(source)
                parsed = urlparse(source)
                
                if parsed.scheme in ('rtsp', 'http', 'https'):
                    # Try FFMPEG first
                    self.capture = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                    if not self.capture.isOpened():
                        # Fallback to default
                        self.capture = cv2.VideoCapture(source)
                else:
                    self.capture = cv2.VideoCapture(f"http://{source}")
            else:
                # Default: try as RTSP with FFMPEG
                source = unquote(source)
                urls_to_try = self._get_rtsp_url_variations(source)
                
                for rtsp_url in urls_to_try:
                    try:
                        self.capture = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                        if self.capture and self.capture.isOpened():
                            ret, frame = self.capture.read()
                            if ret and frame is not None:
                                self.url = rtsp_url
                                break
                    except:
                        continue

            # Check if capture opened successfully
            if not self.capture or not self.capture.isOpened():
                raise Exception(f"VideoCapture could not open source: {self.url}")

            # Reduce startup delay
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Warm up camera - try multiple times
            warmup_frames = 0
            for i in range(30):
                ret, frame = self.capture.read()
                if ret and frame is not None:
                    self.last_frame = frame
                    warmup_frames += 1
                    if warmup_frames >= 3:  # Need at least 3 good frames
                        break
                await asyncio.sleep(0.1)

            if self.last_frame is None:
                raise Exception("Camera opened but no frames received")

            # Get FPS
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            self.fps = fps if fps and fps > 0 else 25

            self.connected = True
            self.is_running = True

            logger.info(f"[Camera {self.camera_id}] Connected successfully (FPS: {self.fps})")
            return True

        except Exception as e:
            logger.error(f"[Camera {self.camera_id}] Connection failed: {e}")
            await self.disconnect()
            return False
    
    def _get_rtsp_url_variations(self, base_url: str) -> list:
        """Generate RTSP URL variations to try for a given base URL"""
        variations = []
        
        # Already complete RTSP URL
        if base_url.startswith('rtsp://'):
            variations.append(base_url)
            return variations
        
        # Parse the base URL
        if '://' in base_url:
            # Has protocol but not rtsp
            base_url = base_url.split('://', 1)[1]
        
        # Extract host and existing port/path if any
        if '/' in base_url:
            host_part, path_part = base_url.split('/', 1)
            path_part = '/' + path_part
        else:
            host_part = base_url
            path_part = None
        
        # Check if host has port
        if ':' in host_part:
            host, port = host_part.rsplit(':', 1)
            # Host already has port
            if path_part:
                variations.append(f"rtsp://{host_part}{path_part}")
            else:
                variations.append(f"rtsp://{host_part}")
                # Also try adding common paths
                for stream_path in ['/stream', '/main', '/ch0', '/preview']:
                    variations.append(f"rtsp://{host_part}{stream_path}")
        else:
            # No port specified, add default RTSP port
            if path_part:
                variations.append(f"rtsp://{host_part}:554{path_part}")
            else:
                # Try without path first
                variations.append(f"rtsp://{host_part}:554")
                # Then with common paths
                for stream_path in ['/stream', '/main', '/ch0', '/preview', '/live']:
                    variations.append(f"rtsp://{host_part}:554{stream_path}")
        
        return variations

    async def get_frame(self):
        """Get a single frame from the camera"""
        if not self.capture or not self.capture.isOpened():
            return None

        try:
            ret, frame = self.capture.read()
            if ret and frame is not None:
                self.last_frame = frame
                return frame
        except Exception as e:
            logger.error(f"[Camera {self.camera_id}] Frame read error: {e}")

        return None

    async def disconnect(self):
        """Disconnect and cleanup camera"""
        self.is_running = False
        self.connected = False

        if self.capture:
            try:
                self.capture.release()
            except Exception as e:
                logger.error(f"[Camera {self.camera_id}] Error releasing capture: {e}")

        self.capture = None
        logger.info(f"[Camera {self.camera_id}] Disconnected")


class CameraManager:
    def __init__(self):
        self.sessions: Dict[str, CameraSession] = {}

    def parse_camera_url(self, url: str, stream_type: str = None) -> str:
        """Parse camera URL input - handle different formats and add defaults"""
        if not url:
            return url
            
        # URL decode first (handle encoded inputs like rtsp%3A%2F%2F)
        decoded = unquote(url).strip()
        
        # If already has protocol, return decoded
        parsed = urlparse(decoded)
        if parsed.scheme in ('rtsp', 'http', 'https'):
            return decoded
        
        # If it's just a number, return as-is (USB camera index)
        if decoded.isdigit():
            return decoded
        
        # If stream_type is rtsp, construct RTSP URL with defaults
        if stream_type and stream_type.lower() == "rtsp":
            # Check if URL already starts with rtsp (shouldn't but be safe)
            if decoded.startswith('rtsp://'):
                return decoded
            
            # Parse to check if it has a port
            if ':' in decoded and not decoded.startswith('['):
                # Has port number already, e.g., "192.168.1.100:554"
                if not decoded.endswith('/'):
                    return f"rtsp://{decoded}"
                return f"rtsp://{decoded}"
            else:
                # No port specified, add default RTSP port 554
                # Also add common stream path if simple IP
                host = decoded.split('/')[0]  # Get just the host part
                path = f"/{'/'.join(decoded.split('/')[1:])}" if '/' in decoded else ""
                
                if not path:
                    # No path specified, try without path first (some cameras don't need it)
                    return f"rtsp://{host}:554"
                else:
                    # Has path, use it
                    return f"rtsp://{host}:554{path}"
        
        # Otherwise assume IP hostname, add http://
        return f"http://{decoded}"

    async def create_session(self, session_id: str, url, camera_id: int, stream_type: str = None):
        """Create a new camera session"""
        # Determine stream type if not provided
        if not stream_type:
            # Auto-detect based on URL
            if url.isdigit():
                stream_type = "usb"
            elif url.startswith(('rtsp://', 'rtsp:')):
                stream_type = "rtsp"
            elif url.startswith(('http://', 'https://')):
                stream_type = "ip"
            else:
                stream_type = "rtsp"  # default
        
        # Parse URL based on stream type
        if isinstance(url, str):
            url = self.parse_camera_url(url, stream_type)
            logger.info(f"[Camera {camera_id}] Parsed URL: {url} (stream_type: {stream_type})")
        
        # Disconnect existing session for same camera
        existing = self.get_session_by_camera_id(camera_id)
        if existing:
            logger.info(f"[Camera {camera_id}] Disconnecting existing session first")
            await existing.disconnect()

        # Create new session
        session = CameraSession(session_id, url, camera_id, stream_type)
        connected = await session.connect()

        if connected:
            self.sessions[session_id] = session
            return session

        return None

    def get_session(self, session_id: str):
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_session_by_camera_id(self, camera_id: int):
        """Get session by camera ID"""
        for session in self.sessions.values():
            if session.camera_id == camera_id:
                return session
        return None

    async def disconnect_session(self, session_id: str):
        """Disconnect and remove session"""
        session = self.sessions.get(session_id)
        if session:
            await session.disconnect()
            del self.sessions[session_id]

    def get_all_sessions(self):
        """Get all active sessions"""
        return self.sessions


# Global instance
camera_manager = CameraManager()