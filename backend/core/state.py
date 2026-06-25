"""
core/state.py — Single Source of Truth for All Shared State
═══════════════════════════════════════════════════════════════════════════════
Design principles:
  • FrameBuffer  — one slot per session; writer always overwrites, reader always
                   gets latest. Zero queue backlog by design.
  • DetectionFlag — a plain dict[session_id → bool] checked atomically in the
                    hot path. No lock needed; CPython's GIL makes bool reads safe.
  • DetectionCache — latest detections per session; overwritten on each cycle.
  • db_write_queue — asyncio.Queue with maxsize; drops oldest on overflow so DB
                     pressure never blocks the event loop.
 
Nothing in this module does any I/O.  Import everywhere without side-effects.
═══════════════════════════════════════════════════════════════════════════════
"""
 
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Frame Buffer  (one slot per session — latest-frame semantics)
# ──────────────────────────────────────────────────────────────────────────────
 
@dataclass
class FrameEntry:
    frame: np.ndarray
    frame_id: int
    ts: float = field(default_factory=time.monotonic)
 
 
class FrameBuffer:
    """
    Thread/coroutine-safe latest-frame store.
 
    Only one frame is kept per session at any time.
    Writers call put(); readers call get().
    No asyncio.Queue — no backlog can form.
    """
 
    def __init__(self) -> None:
        self._store: dict[str, FrameEntry] = {}
 
    def put(self, session_id: str, frame: np.ndarray, frame_id: int) -> None:
        """Overwrite slot with newest frame.  O(1), never blocks."""
        self._store[session_id] = FrameEntry(frame=frame, frame_id=frame_id)
 
    def get(self, session_id: str) -> Optional[FrameEntry]:
        """Return latest entry or None.  O(1), never blocks."""
        return self._store.get(session_id)
 
    def remove(self, session_id: str) -> None:
        self._store.pop(session_id, None)
 
    def __contains__(self, session_id: str) -> bool:
        return session_id in self._store
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Detection toggle  (per-session boolean flag)
# ──────────────────────────────────────────────────────────────────────────────
 
class DetectionFlags:
    """
    Maps session_id → enabled(bool).
 
    Defaults to True (detection ON) for any unknown session.
    Setting a flag takes effect on the very next detection loop iteration —
    no restart required, no queue flush needed.
    """
 
    def __init__(self) -> None:
        self._flags: dict[str, bool] = {}
 
    def enable(self, session_id: str) -> None:
        self._flags[session_id] = True
 
    def disable(self, session_id: str) -> None:
        self._flags[session_id] = False
 
    def is_enabled(self, session_id: str) -> bool:
        return self._flags.get(session_id, True)   # default ON
 
    def toggle(self, session_id: str) -> bool:
        """Flip state, return new state."""
        new = not self.is_enabled(session_id)
        self._flags[session_id] = new
        return new
 
    def remove(self, session_id: str) -> None:
        self._flags.pop(session_id, None)
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Detection Cache  (latest detections per session)
# ──────────────────────────────────────────────────────────────────────────────
 
class DetectionCache:
    """
    Latest detection list per session.
    Overwritten every detection cycle; readers always see the most recent result.
    """
 
    def __init__(self) -> None:
        self._cache: dict[str, list] = {}
 
    def set(self, session_id: str, detections: list) -> None:
        self._cache[session_id] = detections
 
    def get(self, session_id: str) -> list:
        return self._cache.get(session_id, [])
 
    def clear(self, session_id: str) -> None:
        self._cache.pop(session_id, None)
 
 
# ──────────────────────────────────────────────────────────────────────────────
# DB Write Queue  (fire-and-forget; drops under load)
# ──────────────────────────────────────────────────────────────────────────────
 
class DroppableQueue:
    """
    asyncio.Queue wrapper that silently drops the *oldest* item when full
    instead of blocking the caller (put_nowait raises QueueFull; we swallow it).
 
    DB writes are opportunistic: losing a detection record under heavy load is
    acceptable.  Losing video frames or slowing the stream is NOT.
    """
 
    def __init__(self, maxsize: int = 200) -> None:
        self._q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
 
    def put_nowait(self, item) -> bool:
        """Enqueue item.  Returns False if the item was dropped."""
        try:
            self._q.put_nowait(item)
            return True
        except asyncio.QueueFull:
            # Drop oldest, push newest (best-effort)
            try:
                self._q.get_nowait()
                self._q.put_nowait(item)
                return True
            except Exception:
                return False
 
    async def get(self):
        return await self._q.get()
 
    def task_done(self):
        self._q.task_done()
 
    def qsize(self) -> int:
        return self._q.qsize()
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Module-level singletons  (import these everywhere)
# ──────────────────────────────────────────────────────────────────────────────
 
frame_buffer    = FrameBuffer()
detection_flags = DetectionFlags()
detection_cache = DetectionCache()
db_write_queue  = DroppableQueue(maxsize=200)
recording_queue = asyncio.Queue(maxsize=100)