from __future__ import annotations

import cv2
import os
import threading
import logging
import time
import asyncio
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Deque

import numpy as np

logger =  logging.getLogger(__name__)
#===================================================================
# CONFIGURATION (all tunable without touching the rest of the code)
#===================================================================

@dataclass
class SmartRecordingConfig:
    """Central config for the smart recording system.
    Change these values to tune behaviour without editing logic code."""
    
#------- Buffer sizing ---------

    #seconds of footage to keep for pre-recording
    pre_event_seconds: float = 5.0
    
    #How many seconds AFTER the last detection to keep recording.
    post_event_seconds: float = 5.0
    
    # ------- Event-merging -------------------
    # if a new event arrives while the post-event countdown is still running.
    # the deadline is simply extended - clips automaticallt merge.
    # This means any two events closer than the post_event_seconds are merged.
    
    # --------Frame buffer ----------------------
    # JPEG quality for buffer frames
    buffer_jpeg_quality: int=60
    #JPEG quality for final saved clips
    output_jpeg_quality: int=85
    
    #--- Output -----------------------------------
    output_dir: str = "smart_recordings"
    
    #Video codec options tried in order until one works
    codec_priority: List[str] = field(default_factory= lambda: [
        "mp4v", "avc1", "H264", "DIVX"
    ])
    
    #Target FPS for saved clips(None= use camera FPS).
    output_fps: int = None
    
    #Target resolution for saved clips
    output_resolution: Optional[Tuple[int, int]] = None  #width, height
    
    
    #----- Cleanup ----------------------------------
    #Delete clips older than this many days 
    max_clip_age_days: int = 30  # 0= disabled
    
    #maximum total storage for smart_recordings in MB
    max_storage_mb: int = 10_000 
    
    
#======================================================================================
# ENUMS & SMALL DATA CLASSES
#======================================================================================

class RecordingState(Enum):
        """State machine states for a single camera session"""
        IDLE = auto()  # no event active(detected); buffer is rollin silently
        EVENT_ACTIVE = auto() # event detected, deadline being extended
        FINALIZING = auto()  # event finished, writing clip to disk 
     
@dataclass
class BufferedFrame:
    """A single frame stored in the pre-event buffer.
    Storing JPEG bytes instead of raw numpy arrays cuts RAM USAGE BY ~10X
    """
    jpeg_bytes: bytes
    timestamp: float
    has_detections: bool
    detections: List[dict]
    
    def decode(self) -> np.ndarray:
        array = np.frombuffer(self.jpeg_bytes, dtype=np.uint8)
        return cv2.imdecode(array, cv2.IMREAD_COLOR)
    
@dataclass
class ClipRecord:
    """ 
    Metadata for a complete event clip.
    Passed to the background DB writer.
    """
    clip_id: str                      #UUID string for this clip.
    session_id: str                   #Camera session that produced this clip
    camera_id : int
    user_id : int
    filepath: str                     #Absolute path on disk 
    filename : str
    started_at : datetime
    ended_at : datetime
    duration_seconds : float
    file_size_bytes : int 
    frame_count : int 
    detection_count : int  #total detections across all frames
    event_classes : List[str]                  # unique class names detected 
    
    
class RollingFrameBuffer:  
    """
    A thread-safe, FPS-aware circular buffer of JPEG-compressed frames.
 
    Design decisions:
    ─────────────────
    • Uses collections.deque(maxlen=N) which automatically discards the
    oldest frame when the buffer is full — no manual eviction needed.
    • Stores JPEG bytes, not numpy arrays, saving ~10× RAM.
    • maxlen is computed from (fps × pre_event_seconds) so the buffer always
    covers exactly the requested look-back window regardless of camera FPS.
    • Thread-safe via a single threading.Lock().
    """
    
    def __init__(self, fps: float, pre_event_seconds: float, jpeg_quality: int = 60):
        self.fps = max(fps, 1.0)     #Guard against 0 fps
        self.pre_event_seconds = pre_event_seconds
        self.jpeg_quality = jpeg_quality
        
        #Compute how many frames fit in the pre-event window
        #add a 20% margin so we never run short due to fps jitter.
        maxlen = int(self.fps * pre_event_seconds * 1.2)+1
        self._buffer: Deque[BufferedFrame] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        
        logger.debug(
            f"RollingFrameBuffer: fps={fps}, pre={pre_event_seconds}s, "
            f"maxlen= {maxlen} frames"
        )
    
    
    #--------------------------- Public API ------------------------------------
    def push(self, frame:np.ndarray, detections: Optional[List[Dict]] = None
             ) -> BufferedFrame:
        
        """Compress frame to Jpeg and append to the rolling buffer.
        Returns the BufferedFrame that was stored.
        """
        detections = detections or []
        
        #Encode to JPEG for compact storage
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        ok, buf = cv2.imencode('.jpg', frame, encode_params)
        if not ok:
            #Fallback: use default quality
            ok, buf = cv2.imencode('.jpg', frame)
            
        bf = BufferedFrame(
            jpeg_bytes=bytes(buf),
            timestamp= time.time(),
            has_detections = len(detections) > 0,
            detections=detections,
        )
        
        with self._lock:
            self._buffer.append(bf)
            
        return bf
            
    def snapshot(self) -> List[BufferedFrame]:
        """
        Return a shallow copy of all frames currently in the buffer.
        Thread-safe; the returned list is a stable snapshot.
        """
        with self._lock:
            return list(self._buffer)
        
    def clear(self):
        """Empty the buffer (called after a clip is finalised)."""
        with self._lock:
            self._buffer.clear()
            
    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)
        
    @property
    def size_bytes(self) -> int:
        """Approximate RAM used by stored JPEG bytes."""
        with self._lock:
            return sum(len(f.jpeg_bytes) for f in self._buffer)
        
        
# ══════════════════════════════════════════════════════════════════════════════
# PER-SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
 
class SmartSessionState:
    """
    Manages the recording state machine for a single camera session.
 
    State transitions:
    ──────────────────
        IDLE
          │  (detection arrives)
          ▼
      EVENT_ACTIVE  ◄──────────────────────── (new detection extends deadline)
          │  (post_event_seconds pass with no new detection)
          ▼
      FINALIZING  →  background thread writes clip  →  IDLE
 
    All public methods are thread-safe.
    """
 
    def __init__(
        self,
        session_id: str,
        camera_id: int,
        user_id: int,
        fps: float,
        config: SmartRecordingConfig,
    ):
        self.session_id = session_id
        self.camera_id = camera_id
        self.user_id = user_id
        self.fps = fps
        self.config = config
 
        # ── State ──────────────────────────────────────────────────────────
        self._state = RecordingState.IDLE
        self._lock = threading.Lock()
 
        # ── Timers ─────────────────────────────────────────────────────────
        # Wall-clock time of the first detection that opened this event window
        self._event_start_time: Optional[float] = None
        # Wall-clock time of the last detection (deadline = this + post_event_seconds)
        self._last_event_time: Optional[float] = None
 
        # ── Accumulators for the current event window ───────────────────────
        # Frames that accumulate DURING the event (after the event starts)
        self._event_frames: List[BufferedFrame] = []
        self._event_detection_count: int = 0
        self._event_classes: set = set()
 
        # ── Rolling pre-event buffer ───────────────────────────────────────
        self.buffer = RollingFrameBuffer(
            fps=fps,
            pre_event_seconds=config.pre_event_seconds,
            jpeg_quality=config.buffer_jpeg_quality,
        )
 
        # ── Statistics ─────────────────────────────────────────────────────
        self.clips_saved: int = 0
        self.total_detections: int = 0
 
        logger.info(
            f"[SmartSession {session_id}] Initialised "
            f"(cam={camera_id}, fps={fps}, "
            f"pre={config.pre_event_seconds}s, "
            f"post={config.post_event_seconds}s)"
        )
 
    # ── State accessors ───────────────────────────────────────────────────
 
    @property
    def state(self) -> RecordingState:
        with self._lock:
            return self._state
 
    @property
    def is_event_active(self) -> bool:
        with self._lock:
            return self._state == RecordingState.EVENT_ACTIVE
 
    # ── Core frame processing ─────────────────────────────────────────────
 
    def process_frame(self, frame: np.ndarray,
                      detections: Optional[List[Dict]] = None
                      ) -> Optional[List[BufferedFrame]]:
        """
        Main entry point.  Called for every frame from the WebSocket loop.
 
        1. Pushes the frame to the rolling buffer (always).
        2. If detections are present, advances the state machine.
        3. If no detections and we're in EVENT_ACTIVE past the deadline,
           returns the complete list of frames to finalize into a clip.
 
        Returns:
            None              – normal operation, no clip ready yet
            List[BufferedFrame] – clip is ready; these frames should be saved
        """
        detections = detections or []
 
        # Always push to rolling buffer first (even during an active event,
        # so the buffer stays current for the post-event tail)
        bf = self.buffer.push(frame, detections)
 
        with self._lock:
            now = time.time()
 
            if detections:
                # ── Detection arrived ──────────────────────────────────────
                self.total_detections += len(detections)
 
                if self._state == RecordingState.IDLE:
                    # Transition IDLE → EVENT_ACTIVE
                    self._state = RecordingState.EVENT_ACTIVE
                    self._event_start_time = now
                    self._event_frames = []          # reset accumulator
                    self._event_detection_count = 0
                    self._event_classes = set()
                    logger.info(
                        f"[SmartSession {self.session_id}] "
                        f"EVENT START at {datetime.now().strftime('%H:%M:%S')}"
                    )
 
                # Extend post-event deadline (this is the merge mechanism)
                self._last_event_time = now
                self._event_detection_count += len(detections)
                for d in detections:
                    self._event_classes.add(d.get("class_name", "unknown"))
 
                # Accumulate this frame in the event window
                self._event_frames.append(bf)
 
            elif self._state == RecordingState.EVENT_ACTIVE:
                # ── No detection; check if post-event window has expired ───
                self._event_frames.append(bf)  # still accumulate post-event tail
 
                deadline = (self._last_event_time or 0) + self.config.post_event_seconds
                if now >= deadline:
                    # Post-event window closed → build clip and return it
                    self._state = RecordingState.FINALIZING
                    clip_frames = self._build_clip_frames()
                    return clip_frames  # caller will finalize asynchronously
 
            # No clip ready yet
            return None
 
    def finalize_done(self):
        """
        Called by SmartRecordingManager after the clip has been written to disk.
        Resets state back to IDLE.
        """
        with self._lock:
            self._state = RecordingState.IDLE
            self._event_start_time = None
            self._last_event_time = None
            self._event_frames = []
            self._event_detection_count = 0
            self._event_classes = set()
            self.clips_saved += 1
            # Clear the rolling buffer so the next clip starts fresh
            # (buffer will refill within pre_event_seconds of real time)
        self.buffer.clear()
        logger.info(
            f"[SmartSession {self.session_id}] "
            f"STATE → IDLE (clips saved: {self.clips_saved})"
        )
 
    def flush_active_event(self) -> Optional[List[BufferedFrame]]:
        """
        Force-finalize any active event (called on camera disconnect).
        Returns clip frames or None if nothing was recording.
        """
        with self._lock:
            if self._state != RecordingState.EVENT_ACTIVE:
                return None
            self._state = RecordingState.FINALIZING
            return self._build_clip_frames()
 
    # ── Internal helpers ─────────────────────────────────────────────────
 
    def _build_clip_frames(self) -> List[BufferedFrame]:
        """
        Assemble the final ordered frame list:
            [pre-event buffer frames] + [event frames accumulated during event]
 
        We filter the buffer to only include frames within the pre_event window
        relative to _event_start_time, avoiding double-counting frames that
        were pushed to both the buffer and _event_frames.
        """
        cutoff = (self._event_start_time or time.time()) - self.config.pre_event_seconds
        pre_frames = [
            f for f in self.buffer.snapshot()
            if f.timestamp >= cutoff
            and f.timestamp < (self._event_start_time or time.time())
        ]
 
        # _event_frames already contains from event_start onward (including
        # post-event tail), so just concatenate
        all_frames = pre_frames + self._event_frames
 
        logger.info(
            f"[SmartSession {self.session_id}] "
            f"Clip assembled: {len(pre_frames)} pre + "
            f"{len(self._event_frames)} event = {len(all_frames)} total frames | "
            f"classes={self._event_classes}"
        )
        return all_frames
 
    def get_event_metadata(self) -> dict:
        """Return metadata about the current/last event window."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "camera_id": self.camera_id,
                "state": self._state.name,
                "event_start": self._event_start_time,
                "last_detection": self._last_event_time,
                "detection_count": self._event_detection_count,
                "detected_classes": list(self._event_classes),
                "clips_saved": self.clips_saved,
                "buffer_frames": len(self.buffer),
                "buffer_mb": round(self.buffer.size_bytes / 1_048_576, 2),
            }
 
 
# ══════════════════════════════════════════════════════════════════════════════
# CLIP WRITER  (runs in background thread)
# ══════════════════════════════════════════════════════════════════════════════
 
class ClipWriter:
    """
    Writes a list of BufferedFrames to an MP4 file on disk.
 
    Designed to run in a ThreadPoolExecutor so it never blocks the
    async WebSocket event loop.
    """
 
    def __init__(self, config: SmartRecordingConfig):
        self.config = config
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
 
    def write(
        self,
        frames: List[BufferedFrame],
        session_state: SmartSessionState,
        camera_name: str = "camera",
    ) -> Optional[ClipRecord]:
        """
        Decode frames, write to MP4, return ClipRecord metadata.
        Returns None on failure.
        """
        if not frames:
            logger.warning("ClipWriter.write() called with empty frame list")
            return None
 
        # ── Determine output parameters ────────────────────────────────────
        fps = self.config.output_fps or session_state.fps
        fps = max(fps, 1.0)
 
        # Decode first valid frame to get resolution
        sample_frame = None
        for bf in frames:
            sample_frame = bf.decode()
            if sample_frame is not None:
                break
        if sample_frame is None:
            logger.error("ClipWriter: All frames failed to decode")
            return None
 
        if self.config.output_resolution:
            width, height = self.config.output_resolution
        else:
            height, width = sample_frame.shape[:2]
 
        frame_size = (width, height)
 
        # ── Build output filepath ──────────────────────────────────────────
        clip_id = str(uuid.uuid4())[:8]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{camera_name}_event_{ts}_{clip_id}.mp4"
        filepath = os.path.join(self.config.output_dir, filename)
        logger.info(f"SAVING TO: {os.path.abspath(filepath)}")
 
        # ── Open VideoWriter with codec fallback ───────────────────────────
        writer = self._open_writer(filepath, fps, frame_size)
        if writer is None:
            logger.error(f"ClipWriter: Could not open VideoWriter for {filepath}")
            return None
 
        # ── Write frames ───────────────────────────────────────────────────
        written = 0
        detection_count = 0
        event_classes: set = set()
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.output_jpeg_quality]
 
        for bf in frames:
            try:
                frame = bf.decode()
                if frame is None:
                    continue
 
                # Resize if necessary
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, frame_size, interpolation=cv2.INTER_LINEAR)
 
                # Ensure BGR
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                elif frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
 
                writer.write(frame)
                written += 1
 
                if bf.has_detections:
                    detection_count += len(bf.detections)
                    for d in bf.detections:
                        event_classes.add(d.get("class_name", "unknown"))
 
            except Exception as e:
                logger.warning(f"ClipWriter: Frame write error: {e}")
                continue
 
        writer.release()
 
        # ── Validate output ────────────────────────────────────────────────
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        if file_size == 0:
            logger.error(f"ClipWriter: Output file is empty: {filepath}")
            return None
 
        duration = written / fps if fps > 0 else 0
        started_at = datetime.fromtimestamp(frames[0].timestamp)
        ended_at = datetime.fromtimestamp(frames[-1].timestamp)
 
        record = ClipRecord(
            clip_id=clip_id,
            session_id=session_state.session_id,
            camera_id=session_state.camera_id,
            user_id=session_state.user_id,
            filepath=filepath,
            filename=filename,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=round(duration, 2),
            file_size_bytes=file_size,
            frame_count=written,
            detection_count=detection_count,
            event_classes=sorted(event_classes),
        )
 
        logger.info(
            f"✅ Clip saved: {filename} "
            f"({written} frames, {duration:.1f}s, "
            f"{file_size/1_048_576:.2f}MB, "
            f"classes={sorted(event_classes)})"
        )
        return record
 
    def _open_writer(self, filepath: str, fps: float,
                     frame_size: Tuple[int, int]) -> Optional[cv2.VideoWriter]:
        """Try each codec in priority order; return first working writer."""
        for codec in self.config.codec_priority:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                writer = cv2.VideoWriter(filepath, fourcc, fps, frame_size)
                if writer.isOpened():
                    logger.debug(f"ClipWriter: Using codec '{codec}'")
                    return writer
                writer.release()
            except Exception as e:
                logger.debug(f"ClipWriter: Codec '{codec}' failed: {e}")
        return None
 
 
# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND DB WRITER
# ══════════════════════════════════════════════════════════════════════════════
 
def _save_clip_to_db(clip: ClipRecord, db_session_factory) -> bool:
    """
    Persist a completed clip as a Recording row in the database.
    Runs in a background thread.
 
    Args:
        clip:               ClipRecord with all metadata
        db_session_factory: Callable that returns a new SQLAlchemy Session
                            (i.e. SessionLocal from database.py)
    """
    try:
        from database import Recording   # local import to avoid circular deps
        db = db_session_factory()
        try:
            recording = Recording(
                filename=clip.filename,
                format="mp4",
                duration_seconds=int(clip.duration_seconds),
                file_size_bytes=clip.file_size_bytes,
                storage_path=clip.filepath,
                camera_id=clip.camera_id,
                user_id=clip.user_id,
                started_at=clip.started_at,
                ended_at=clip.ended_at,
                is_scheduled=False,      # event-driven, not schedule-driven
                # store event classes in the filename field as context
                # (the existing schema has no free-form metadata column)
            )
            db.add(recording)
            db.commit()
            db.refresh(recording)
            logger.info(
                f"DB: Clip {clip.filename} saved as Recording id={recording.id}"
            )
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"DB: Error saving clip {clip.filename}: {e}")
            return False
        finally:
            db.close()
    except Exception as e:
        logger.error(f"DB: Fatal error in _save_clip_to_db: {e}")
        return False
 
 
# ══════════════════════════════════════════════════════════════════════════════
# STORAGE CLEANUP
# ══════════════════════════════════════════════════════════════════════════════
 
class StorageCleanup:
    """
    Periodic background task that enforces storage limits.
 
    Strategies (applied in order):
      1. Delete clips older than max_clip_age_days.
      2. If total storage still exceeds max_storage_mb, delete oldest clips
         until we're back under the limit.
    """
 
    def __init__(self, config: SmartRecordingConfig):
        self.config = config
        self._lock = threading.Lock()
 
    def run(self) -> dict:
        """
        Execute cleanup and return a summary dict.
        Thread-safe; can be called from any thread.
        """
        with self._lock:
            return self._cleanup()
 
    def _cleanup(self) -> dict:
        output_dir = Path(self.config.output_dir)
        if not output_dir.exists():
            return {"deleted": 0, "freed_bytes": 0}
 
        clips = sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
        deleted = 0
        freed = 0
        now = time.time()
 
        # ── Age-based deletion ─────────────────────────────────────────────
        if self.config.max_clip_age_days > 0:
            age_limit = self.config.max_clip_age_days * 86_400
            still_valid = []
            for clip in clips:
                age = now - clip.stat().st_mtime
                if age > age_limit:
                    size = clip.stat().st_size
                    clip.unlink(missing_ok=True)
                    freed += size
                    deleted += 1
                    logger.info(f"Cleanup (age): deleted {clip.name}")
                else:
                    still_valid.append(clip)
            clips = still_valid
 
        # ── Storage cap deletion (oldest-first) ───────────────────────────
        if self.config.max_storage_mb > 0:
            cap = self.config.max_storage_mb * 1_048_576
            total = sum(c.stat().st_size for c in clips)
            for clip in clips:
                if total <= cap:
                    break
                size = clip.stat().st_size
                clip.unlink(missing_ok=True)
                total -= size
                freed += size
                deleted += 1
                logger.info(f"Cleanup (cap): deleted {clip.name}")
 
        return {
            "deleted": deleted,
            "freed_bytes": freed,
            "freed_mb": round(freed / 1_048_576, 2),
        }
 
 
# ══════════════════════════════════════════════════════════════════════════════
# SMART RECORDING MANAGER  (the public API used by app.py)
# ══════════════════════════════════════════════════════════════════════════════
 
class SmartRecordingManager:
    """
    Top-level coordinator.  One global instance shared across all sessions.
 
    Public API used by app.py:
    ──────────────────────────
        smart_recording_manager.init_session(session_id, camera_id, user_id,
                                             fps, camera_name)
        smart_recording_manager.push_frame(session_id, frame, detections)
        smart_recording_manager.close_session(session_id)
        smart_recording_manager.get_status(session_id)
        smart_recording_manager.get_all_statuses()
        smart_recording_manager.run_cleanup()
    """
 
    def __init__(
        self,
        config: Optional[SmartRecordingConfig] = None,
        db_session_factory=None,
        max_workers: int = 4,
    ):
        """
        Args:
            config:              SmartRecordingConfig (uses defaults if None)
            db_session_factory:  Callable → SQLAlchemy Session (SessionLocal)
            max_workers:         Thread pool size for background clip writes
        """
        self.config = config or SmartRecordingConfig()
        self._db_factory = db_session_factory  # set later via set_db_factory()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="smart_rec"
        )
        self._sessions: Dict[str, SmartSessionState] = {}
        self._camera_names: Dict[str, str] = {}       # session_id → camera_name
        self._sessions_lock = threading.Lock()
        self._clip_writer = ClipWriter(self.config)
        self._cleanup = StorageCleanup(self.config)
 
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(
            f"SmartRecordingManager initialised "
            f"(output={self.config.output_dir}, "
            f"pre={self.config.pre_event_seconds}s, "
            f"post={self.config.post_event_seconds}s)"
        )
 
    def set_db_factory(self, factory):
        """Inject the database session factory (called from app.py startup)."""
        self._db_factory = factory
        logger.info("SmartRecordingManager: DB factory injected")
 
    # ── Session lifecycle ─────────────────────────────────────────────────
 
    def init_session(
        self,
        session_id: str,
        camera_id: int,
        user_id: int,
        fps: float,
        camera_name: str = "camera",
    ) -> SmartSessionState:
        """
        Register a camera session.  Call this when the WebSocket connects.
 
        Args:
            session_id:  WebSocket/camera session UUID
            camera_id:   DB camera ID
            user_id:     DB user ID
            fps:         Camera FPS (used to size the buffer)
            camera_name: Used in output filenames
        """
        with self._sessions_lock:
            if session_id in self._sessions:
                logger.warning(
                    f"SmartRecordingManager: session {session_id} already exists, "
                    "reinitialising"
                )
 
            state = SmartSessionState(
                session_id=session_id,
                camera_id=camera_id,
                user_id=user_id,
                fps=fps,
                config=self.config,
            )
            self._sessions[session_id] = state
            self._camera_names[session_id] = camera_name
 
        logger.info(
            f"SmartRecordingManager: session registered "
            f"(id={session_id}, cam={camera_id}, fps={fps})"
        )
        return state
 
    def close_session(self, session_id: str):
        """
        Deregister a session.  If an event is active, force-finalises the clip.
        Call this on camera disconnect.
        """
        with self._sessions_lock:
            state = self._sessions.pop(session_id, None)
            camera_name = self._camera_names.pop(session_id, "camera")
 
        if state is None:
            return
 
        # If there's an active event, flush it to disk
        clip_frames = state.flush_active_event()
        if clip_frames:
            logger.info(
                f"SmartRecordingManager: flushing active event on close "
                f"for session {session_id}"
            )
            self._submit_clip(clip_frames, state, camera_name)
 
        logger.info(f"SmartRecordingManager: session closed ({session_id})")
 
    # ── Core frame ingestion ──────────────────────────────────────────────
 
    def push_frame(
        self,
        session_id: str,
        frame: np.ndarray,
        detections: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Main per-frame hook.  Call this from the WebSocket loop instead of
        recording_manager.write_frame().
 
        Replaces these two lines in app.py:
            if recording_manager.is_recording(session_id):
                recording_manager.write_frame(session_id, recording_frame)
 
        With just:
            smart_recording_manager.push_frame(session_id, recording_frame,
                                               detections)
 
        Args:
            session_id:  Current WebSocket session
            frame:       BGR numpy frame (with detections drawn if desired)
            detections:  List of detection dicts from yolo_detector.detect()
 
        Returns:
            True if handled, False if session not registered
        """
        with self._sessions_lock:
            state = self._sessions.get(session_id)
 
        if state is None:
            return False
 
        # Delegate to state machine; returns frames if a clip is ready
        clip_frames = state.process_frame(frame, detections)
 
        if clip_frames is not None:
            # Clip is ready → write asynchronously in background thread
            camera_name = self._camera_names.get(session_id, "camera")
            self._submit_clip(clip_frames, state, camera_name)
 
        return True
 
    # ── Status queries ────────────────────────────────────────────────────
 
    def get_status(self, session_id: str) -> Optional[dict]:
        """Return current state metadata for a session."""
        with self._sessions_lock:
            state = self._sessions.get(session_id)
        if state is None:
            return None
        return state.get_event_metadata()
 
    def get_all_statuses(self) -> Dict[str, dict]:
        """Return status for all active sessions."""
        with self._sessions_lock:
            session_ids = list(self._sessions.keys())
        return {sid: self.get_status(sid) for sid in session_ids}
 
    def is_event_active(self, session_id: str) -> bool:
        """True if a detection event is currently being recorded."""
        with self._sessions_lock:
            state = self._sessions.get(session_id)
        return state.is_event_active if state else False
 
    # ── Storage cleanup ───────────────────────────────────────────────────
 
    def run_cleanup(self) -> dict:
        """
        Run storage cleanup synchronously (can be called from a background
        task or FastAPI startup event).
        """
        result = self._cleanup.run()
        logger.info(f"Storage cleanup: {result}")
        return result
 
    def get_storage_stats(self) -> dict:
        """Return storage usage statistics for smart_recordings directory."""
        output_dir = Path(self.config.output_dir)
        if not output_dir.exists():
            return {"total_clips": 0, "total_bytes": 0, "total_mb": 0.0}
 
        clips = list(output_dir.glob("*.mp4"))
        total_bytes = sum(c.stat().st_size for c in clips)
        return {
            "total_clips": len(clips),
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / 1_048_576, 2),
            "output_dir": str(output_dir.resolve()),
        }
 
    # ── Internal helpers ──────────────────────────────────────────────────
 
    def _submit_clip(
        self,
        frames: List[BufferedFrame],
        state: SmartSessionState,
        camera_name: str,
    ):
        """
        Submit clip writing to the thread pool executor.
        Never blocks the calling async loop.
        """
        # Capture references needed inside the thread
        db_factory = self._db_factory
        writer = self._clip_writer
 
        def _task():
            try:
                clip = writer.write(frames, state, camera_name)
                if clip and db_factory:
                    _save_clip_to_db(clip, db_factory)
            except Exception as e:
                logger.error(f"Clip finalisation error: {e}", exc_info=True)
            finally:
                # Always reset the state machine, even on failure
                state.finalize_done()
 
        self._executor.submit(_task)
        logger.debug(
            f"SmartRecordingManager: clip task submitted for session "
            f"{state.session_id} ({len(frames)} frames)"
        )
 
 
# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ══════════════════════════════════════════════════════════════════════════════
 
# Created with default config.
# Call smart_recording_manager.set_db_factory(SessionLocal) in app.py startup.
smart_recording_manager = SmartRecordingManager()