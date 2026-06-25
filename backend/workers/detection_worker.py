"""
workers/detection_worker.py — Fully Decoupled Detection Pipeline
═══════════════════════════════════════════════════════════════════════════════
Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │  detection_worker(session_id)           [asyncio Task]      │
  │                                                             │
  │   1. Check detection_flags.is_enabled() → skip if OFF       │
  │   2. Read frame_buffer.get()            → skip if stale     │
  │   3. Skip if same frame_id as last run  → no duplicate work │
  │   4. asyncio.to_thread(yolo.detect())   → never blocks loop │
  │   5. detection_cache.set()              → update cache      │
  │   6. db_write_queue.put_nowait()        → fire-and-forget   │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │  db_writer_worker()                     [asyncio Task]      │
  │                                                             │
  │   • Drains db_write_queue                                   │
  │   • Runs blocking SQLAlchemy write in thread pool           │
  │   • Never touches the event loop's hot path                 │
  └─────────────────────────────────────────────────────────────┘

Key contracts:
  • No import from camera_handler → zero streaming coupling.
  • db_write_queue drops under load; that is intentional and safe.
  • Detection toggle takes effect within one loop iteration (~30 ms).
  • YOLO inference always runs in a thread; event loop is never blocked.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from core.state import (
    frame_buffer,
    detection_flags,
    detection_cache,
    db_write_queue,
)
from yolo_detector import yolo_detector
from database import SessionLocal, Detection

logger = logging.getLogger(__name__)

# Detection loop cadence when detection IS enabled.
DETECTION_INTERVAL_S = 0.033   # ~30 fps ceiling for detection
DETECTION_IDLE_S     = 0.10    # sleep when detection is disabled
FRAME_STALE_S        = 1.5     # ignore frames older than this


# ──────────────────────────────────────────────────────────────────────────────
# Per-session detection loop
# ──────────────────────────────────────────────────────────────────────────────

async def detection_worker(session_id: str) -> None:
    """
    Runs as an asyncio.Task per active camera session.

    Stop it by cancelling the task — CancelledError is caught cleanly.
    Detection can also be toggled ON/OFF at any time via detection_flags
    without cancelling or restarting the task.
    """
    last_frame_id: int = -1
    logger.info(f"[DetectionWorker] Started  session={session_id}")

    while True:
        try:
            # ── 1. Toggle check (instant, no lock needed) ──────────────────
            if not detection_flags.is_enabled(session_id):
                await asyncio.sleep(DETECTION_IDLE_S)
                continue

            # ── 2. Grab latest frame entry ─────────────────────────────────
            entry = frame_buffer.get(session_id)
            if entry is None:
                await asyncio.sleep(DETECTION_IDLE_S)
                continue

            # ── 3. Skip stale frames ───────────────────────────────────────
            age = time.monotonic() - entry.ts
            if age > FRAME_STALE_S:
                await asyncio.sleep(DETECTION_IDLE_S)
                continue

            # ── 4. Skip duplicate frame (same frame_id) ────────────────────
            if entry.frame_id == last_frame_id:
                await asyncio.sleep(DETECTION_INTERVAL_S)
                continue

            last_frame_id = entry.frame_id
            frame = entry.frame          # local ref — safe to use in thread

            # ── 5. Run YOLO in thread pool (never blocks event loop) ────────
            detections: list = await asyncio.to_thread(
                yolo_detector.detect, frame, 0.30
            )

            # ── 6. Update detection cache (latest result for this session) ──
            detection_cache.set(session_id, detections)

            # ── 7. Enqueue DB write (fire-and-forget; drops if queue full) ──
            if detections:
                dropped = not db_write_queue.put_nowait(
                    (session_id, detections, frame)
                )
                if dropped:
                    logger.debug(
                        f"[DetectionWorker] DB queue full — detection dropped"
                        f"  session={session_id}"
                    )

            await asyncio.sleep(DETECTION_INTERVAL_S)

        except asyncio.CancelledError:
            logger.info(f"[DetectionWorker] Cancelled  session={session_id}")
            detection_cache.clear(session_id)
            break
        except Exception as exc:
            logger.error(f"[DetectionWorker] Error  session={session_id}: {exc}")
            await asyncio.sleep(0.5)   # back off on unexpected errors


# ──────────────────────────────────────────────────────────────────────────────
# Shared DB writer  (one global task drains db_write_queue)
# ──────────────────────────────────────────────────────────────────────────────

async def db_writer_worker() -> None:
    """
    Single global asyncio Task.  Drains db_write_queue continuously.
    All SQLAlchemy work runs in a thread pool — never blocks the event loop.
    """
    logger.info("[DBWriter] Started")

    while True:
        try:
            session_id, detections, frame = await db_write_queue.get()

            # Blocking DB write — offloaded to thread pool
            await asyncio.to_thread(
                _write_detections_sync, session_id, detections, frame
            )

            db_write_queue.task_done()

        except asyncio.CancelledError:
            logger.info("[DBWriter] Cancelled")
            break
        except Exception as exc:
            logger.error(f"[DBWriter] Unexpected error: {exc}")
            await asyncio.sleep(0.2)


def _write_detections_sync(
    camera_id: str,
    detections: list,
    frame,
) -> None:
    """
    Blocking.  Runs via asyncio.to_thread().
    Opens its own DB session, writes, closes.  Never shares a session
    with the FastAPI request handlers.
    """
    db = SessionLocal()
    try:
        for det in detections:
            bbox = det.get("bbox", {})
            screenshot_path: Optional[str] = None

            try:
                screenshot_path = yolo_detector.save_detection(
                    frame, det, output_dir="detections"
                )
            except Exception as exc:
                logger.warning(f"[DBWriter] Screenshot failed: {exc}")

            db.add(
                Detection(
                    camera_id=camera_id,
                    class_name=det.get("class_name", "unknown"),
                    confidence=det.get("confidence", 0.0),
                    bbox_x1=bbox.get("x1", 0),
                    bbox_y1=bbox.get("y1", 0),
                    bbox_x2=bbox.get("x2", 0),
                    bbox_y2=bbox.get("y2", 0),
                    screenshot_path=screenshot_path,
                    detected_at=datetime.utcnow(),
                )
            )

        db.commit()
        logger.debug(
            f"[DBWriter] Saved {len(detections)} detections  camera={camera_id}"
        )

    except Exception as exc:
        db.rollback()
        logger.error(f"[DBWriter] Commit failed  camera={camera_id}: {exc}")
    finally:
        db.close()