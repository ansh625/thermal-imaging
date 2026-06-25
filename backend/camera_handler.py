"""
camera_handler.py — Pure Frame Capture, Zero Detection Coupling
═══════════════════════════════════════════════════════════════════════════════
Architecture guarantees:
  • CameraSession.camera_loop() runs as an asyncio Task that does ONE thing:
    read the next frame from cv2 and write it to frame_buffer.put().
  • The loop calls asyncio.to_thread() for the blocking cv2.VideoCapture.read()
    so it NEVER stalls the event loop, even on a slow RTSP stream.
  • No detection, no DB, no WebSocket code lives here.
  • Reconnect logic is self-contained inside _read_frame_thread().

Concurrency model:
  ┌─────────────────────────┐
  │  Thread pool            │  ← cv2.VideoCapture.read()  (blocking I/O)
  │  (asyncio.to_thread)    │
  └──────────┬──────────────┘
             │  frame (np.ndarray)
  ┌──────────▼──────────────┐
  │  Event loop             │  ← frame_buffer.put()  (non-blocking dict write)
  │  (camera_loop task)     │
  └─────────────────────────┘
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Optional
from urllib.parse import unquote, urlparse

import cv2
import numpy as np

from core.state import frame_buffer

logger = logging.getLogger(__name__)

# How long (seconds) a frame is considered "fresh" for the WebSocket sender.
FRAME_STALE_SECONDS = 2.0

# Frames to grab-and-discard to drain the internal cv2 buffer before retrieve().
CV2_DRAIN_COUNT = 4


# ──────────────────────────────────────────────────────────────────────────────
# CameraSession
# ──────────────────────────────────────────────────────────────────────────────

class CameraSession:
    def __init__(
        self,
        session_id: str,
        url: str | int,
        camera_id: int,
        stream_type: str = "rtsp",
    ) -> None:
        self.session_id = session_id
        self.url = url
        self.camera_id = camera_id
        self.stream_type = (stream_type or "rtsp").lower()

        self.capture: Optional[cv2.VideoCapture] = None
        self.connected = False
        self.is_running = False
        self.fps: float = 10.0
        self._frame_id: int = 0
        self._task: Optional[asyncio.Task] = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Open the camera and start the background capture loop."""
        try:
            cap = await asyncio.to_thread(self._open_capture)
            if cap is None:
                return False

            self.capture = cap
            detected_fps = cap.get(cv2.CAP_PROP_FPS)
            self.fps = detected_fps if detected_fps and detected_fps > 0 else 10.0

            self.connected = True
            self.is_running = True
            self._task = asyncio.create_task(
                self._camera_loop(), name=f"cam-loop-{self.session_id}"
            )
            logger.info(
                f"[Camera {self.camera_id}] Connected  fps={self.fps:.1f}"
                f"  session={self.session_id}"
            )
            return True

        except Exception as exc:
            logger.error(f"[Camera {self.camera_id}] connect() failed: {exc}")
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Stop the capture loop and release resources."""
        self.is_running = False
        self.connected = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self.capture:
            await asyncio.to_thread(self.capture.release)
            self.capture = None

        frame_buffer.remove(self.session_id)
        logger.info(f"[Camera {self.camera_id}] Disconnected")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        """
        Blocking.  Run via asyncio.to_thread().
        Tries all URL variants for RTSP; returns None on failure.
        """
        urls = self._resolve_urls()

        for url in urls:
            cap = self._try_open(url)
            if cap is not None:
                self.url = url          # remember the URL that worked
                return cap

        logger.error(
            f"[Camera {self.camera_id}] Could not open any of: {urls}"
        )
        return None

    def _try_open(self, url) -> Optional[cv2.VideoCapture]:
        """Open one URL; return VideoCapture on success, None otherwise."""
        try:
            backend = (
                cv2.CAP_DSHOW
                if self.stream_type == "usb"
                else cv2.CAP_FFMPEG
            )
            cap = cv2.VideoCapture(url, backend)
            if not cap or not cap.isOpened():
                return None

            # Minimise internal buffering
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Verify at least one readable frame
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None:
                    return cap

            cap.release()
        except Exception as exc:
            logger.debug(f"[Camera {self.camera_id}] _try_open({url}): {exc}")
        return None

    def _resolve_urls(self) -> list:
        """Return an ordered list of URLs to try."""
        raw = unquote(str(self.url)).strip()

        if self.stream_type == "usb":
            idx = int(raw) if raw.isdigit() else 0
            return [idx]

        if self.stream_type in ("rtsp", "raw") and not raw.startswith("rtsp://"):
            return self._rtsp_variations(raw)

        return [raw]

    @staticmethod
    def _rtsp_variations(base: str) -> list:
        """Generate candidate RTSP URLs from a bare host[:port][/path] string."""
        # Strip any leading protocol
        if "://" in base:
            base = base.split("://", 1)[1]

        if "/" in base:
            host_part, path = base.split("/", 1)
            path = "/" + path
        else:
            host_part, path = base, ""

        has_port = ":" in host_part

        if path:
            return [f"rtsp://{host_part}{path}"]

        if has_port:
            candidates = ["", "/stream", "/main", "/ch0", "/preview"]
            return [f"rtsp://{host_part}{p}" for p in candidates]
        else:
            candidates = ["", "/stream", "/main", "/ch0", "/preview", "/live"]
            return [f"rtsp://{host_part}:554{p}" for p in candidates]

    # ── Camera loop (asyncio Task) ────────────────────────────────────────────

    async def _camera_loop(self) -> None:
        """
        Grab the newest frame from the camera as fast as possible and write it
        to frame_buffer.  The blocking read happens in a thread pool.

        Key properties:
          • Never blocks the event loop.
          • Drops old frames automatically (grab() drains the buffer).
          • On read failure, backs off briefly then retries.
          • On repeated failures, logs and exits (caller can reconnect).
        """
        consecutive_failures = 0
        MAX_FAILURES = 30

        while self.is_running:
            try:
                frame = await asyncio.to_thread(self._read_latest_frame)

                if frame is not None:
                    consecutive_failures = 0
                    self._frame_id += 1
                    frame_buffer.put(self.session_id, frame, self._frame_id)
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= MAX_FAILURES:
                        logger.warning(
                            f"[Camera {self.camera_id}] {MAX_FAILURES} consecutive"
                            " read failures — stopping loop"
                        )
                        self.connected = False
                        break
                    await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[Camera {self.camera_id}] Loop error: {exc}")
                await asyncio.sleep(0.1)

    def _read_latest_frame(self) -> Optional[np.ndarray]:
        """
        Blocking.  Called via asyncio.to_thread().
        Drains buffered frames then retrieves the latest one.
        Returns the frame ndarray or None on failure.
        """
        if not self.capture or not self.capture.isOpened():
            return None

        # Drain old buffered frames (keep only the very latest)
        for _ in range(CV2_DRAIN_COUNT):
            self.capture.grab()

        ret, frame = self.capture.retrieve()
        if ret and frame is not None:
            return frame

        # retrieve() failed; try a full read() as fallback
        ret, frame = self.capture.read()
        return frame if ret and frame is not None else None


# ──────────────────────────────────────────────────────────────────────────────
# CameraManager
# ──────────────────────────────────────────────────────────────────────────────

class CameraManager:
    def __init__(self) -> None:
        self.sessions: Dict[str, CameraSession] = {}

    def parse_url(self, url: str, stream_type: Optional[str] = None) -> str:
        """Normalise URL; add missing protocol for IP cameras."""
        decoded = unquote(url).strip()
        parsed = urlparse(decoded)
        if parsed.scheme in ("rtsp", "http", "https"):
            return decoded
        if decoded.isdigit():
            return decoded
        if stream_type and stream_type.lower() == "rtsp":
            host = decoded.split("/")[0]
            path = f"/{'/'.join(decoded.split('/')[1:])}" if "/" in decoded else ""
            sep = "" if ":" in host else ":554"
            return f"rtsp://{host}{sep}{path}"
        return f"http://{decoded}"

    async def create_session(
        self,
        session_id: str,
        url: str | int,
        camera_id: int,
        stream_type: Optional[str] = None,
    ) -> Optional[CameraSession]:
        """Create and connect a camera session."""
        # Auto-detect stream type
        if not stream_type:
            raw = str(url)
            if raw.isdigit():
                stream_type = "usb"
            elif raw.startswith(("rtsp://", "rtsp:")):
                stream_type = "rtsp"
            elif raw.startswith(("http://", "https://")):
                stream_type = "ip"
            else:
                stream_type = "rtsp"

        # Normalise URL
        if isinstance(url, str):
            url = self.parse_url(url, stream_type)

        # Disconnect any existing session for this camera
        old = self.get_by_camera_id(camera_id)
        if old:
            await old.disconnect()
            self.sessions.pop(old.session_id, None)

        session = CameraSession(session_id, url, camera_id, stream_type)
        if await session.connect():
            self.sessions[session_id] = session
            return session
        return None

    def get(self, session_id: str) -> Optional[CameraSession]:
        return self.sessions.get(session_id)

    def get_by_camera_id(self, camera_id: int) -> Optional[CameraSession]:
        return next(
            (s for s in self.sessions.values() if s.camera_id == camera_id),
            None,
        )

    async def disconnect(self, session_id: str) -> None:
        session = self.sessions.pop(session_id, None)
        if session:
            await session.disconnect()

    @property
    def all_sessions(self) -> Dict[str, CameraSession]:
        return self.sessions


# Module-level singleton
camera_manager = CameraManager()