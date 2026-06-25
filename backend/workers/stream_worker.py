"""
workers/stream_worker.py — WebSocket Frame Sender
═══════════════════════════════════════════════════════════════════════════════
One asyncio Task per WebSocket connection.  It:

  1. Reads the latest frame from frame_buffer   (non-blocking dict lookup)
  2. Optionally overlays detection boxes        (CPU-bound, in thread)
  3. JPEG-encodes the frame                     (CPU-bound, in thread)
  4. Sends the base64 payload over WebSocket

Why this is always smooth:
  • frame_buffer is a single slot — no queue, no head-of-line blocking.
  • If no NEW frame arrived since last send, we skip and wait.
  • CPU work (draw + JPEG encode) is in a thread pool — never stalls the loop.
  • WebSocket send failures cancel the task cleanly; they never affect the
    camera loop or detection worker.

Target send rate: ~TARGET_FPS (default 25).  Actual rate is capped by how fast
the camera delivers frames; it can never exceed it.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Optional

import cv2
import numpy as np
from fastapi import WebSocket

from core.state import frame_buffer, detection_cache, detection_flags
from yolo_detector import yolo_detector

logger = logging.getLogger(__name__)

TARGET_FPS = 25
SEND_INTERVAL = 1.0 / TARGET_FPS   # ~0.040 s
FRAME_STALE_S = 2.0                # don't send frames older than this


# ──────────────────────────────────────────────────────────────────────────────
# Helpers (all blocking — called via asyncio.to_thread)
# ──────────────────────────────────────────────────────────────────────────────

def _encode_frame(frame: np.ndarray, detections: list, overlay: bool) -> Optional[bytes]:
    """
    Blocking.  Draw detection overlays (optional) then JPEG-encode.
    Returns raw bytes or None on failure.
    """
    try:
        if overlay and detections:
            frame = yolo_detector.draw_detections(frame, detections)

        ret, buf = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
        )
        return bytes(buf) if ret else None
    except Exception as exc:
        logger.warning(f"[StreamWorker] Encode error: {exc}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Per-connection streaming task
# ──────────────────────────────────────────────────────────────────────────────

async def stream_worker(
    websocket: WebSocket,
    session_id: str,
    show_detections: bool = True,
) -> None:
    """
    Runs as an asyncio Task for the lifetime of one WebSocket connection.

    Cancel this task to stop streaming.  The camera loop is unaffected.
    """
    last_sent_id: int = -1
    logger.info(f"[StreamWorker] Started  session={session_id}")

    while True:
        try:
            loop_start = time.monotonic()

            # ── 1. Latest frame (O(1) dict lookup) ────────────────────────
            entry = frame_buffer.get(session_id)

            if entry is None:
                await asyncio.sleep(SEND_INTERVAL)
                continue

            # ── 2. Skip stale frames ───────────────────────────────────────
            age = time.monotonic() - entry.ts
            if age > FRAME_STALE_S:
                await asyncio.sleep(SEND_INTERVAL)
                continue

            # ── 3. Skip if no new frame since last send ────────────────────
            if entry.frame_id == last_sent_id:
                # Sleep only the remainder of the interval to cap CPU
                elapsed = time.monotonic() - loop_start
                await asyncio.sleep(max(0.0, SEND_INTERVAL - elapsed))
                continue

            last_sent_id = entry.frame_id
            frame = entry.frame

            # ── 4. Get cached detections (zero-cost; already computed) ─────
            detections = (
                detection_cache.get(session_id)
                if detection_flags.is_enabled(session_id)
                else []
            )

            # ── 5. Encode in thread pool ───────────────────────────────────
            jpeg_bytes = await asyncio.to_thread(
                _encode_frame, frame, detections, show_detections
            )
            if jpeg_bytes is None:
                await asyncio.sleep(SEND_INTERVAL)
                continue

            # ── 6. Send over WebSocket ─────────────────────────────────────
            b64 = base64.b64encode(jpeg_bytes).decode("ascii")
            payload = {
                "type": "frame",
                "data": b64,
                "session_id": session_id,
                "frame_id": last_sent_id,
                "detection_count": len(detections),
                "ts": loop_start,
            }
            await websocket.send_json(payload)

            # ── 7. Pace to TARGET_FPS ──────────────────────────────────────
            elapsed = time.monotonic() - loop_start
            await asyncio.sleep(max(0.0, SEND_INTERVAL - elapsed))

        except asyncio.CancelledError:
            logger.info(f"[StreamWorker] Cancelled  session={session_id}")
            break
        except Exception as exc:
            logger.warning(f"[StreamWorker] Error  session={session_id}: {exc}")
            break   # WebSocket is likely closed; exit cleanly