"""
api/camera_routes.py — Camera & Detection API Routes
═══════════════════════════════════════════════════════════════════════════════
Demonstrates how all the refactored pieces plug together:

  POST /api/cameras/{id}/connect          → create CameraSession + detection task
  DELETE /api/cameras/{id}/disconnect     → tear down session + tasks
  POST /api/cameras/{id}/detection/toggle → flip DetectionFlag instantly
  GET  /api/cameras/{id}/detection/status → current flag + cached results
  WS   /ws/stream/{session_id}            → video stream (latest frame only)

Every endpoint is non-blocking.
WebSocket handler composes stream_worker as a task and awaits it.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from camera_handler import camera_manager
from core.state import detection_flags, detection_cache, frame_buffer, db_write_queue
from database import get_db, Camera
from workers.detection_worker import detection_worker
from workers.stream_worker import stream_worker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cameras", tags=["cameras"])

# Tracks the detection asyncio.Task per session so we can cancel it cleanly.
_detection_tasks: dict[str, asyncio.Task] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    url: str
    stream_type: Optional[str] = None   # usb | rtsp | ip | raw


class ConnectResponse(BaseModel):
    session_id: str
    camera_id: int
    fps: float
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# Connect
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{camera_id}/connect", response_model=ConnectResponse)
async def connect_camera(
    camera_id: int,
    body: ConnectRequest,
    db: Session = Depends(get_db),
):
    """
    1. Open the camera (non-blocking; cv2.open runs in thread).
    2. Start the detection asyncio.Task for this session.
    3. Return session_id to the client — it uses this to open the WS stream.
    """
    session_id = str(uuid.uuid4())

    session = await camera_manager.create_session(
        session_id=session_id,
        url=body.url,
        camera_id=camera_id,
        stream_type=body.stream_type,
    )
    if session is None:
        raise HTTPException(status_code=502, detail="Could not open camera")

    # Enable detection by default for new sessions
    detection_flags.enable(session_id)

    # Start per-session detection task
    task = asyncio.create_task(
        detection_worker(session_id),
        name=f"detection-{session_id}",
    )
    _detection_tasks[session_id] = task

    # Update DB camera record
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if cam:
        cam.status = "connected"
        cam.session_id = session_id
        cam.last_seen = datetime.utcnow()
        cam.fps = session.fps
        db.commit()

    logger.info(f"[API] Camera {camera_id} connected  session={session_id}")
    return ConnectResponse(
        session_id=session_id,
        camera_id=camera_id,
        fps=session.fps,
        message="Camera connected",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Disconnect
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/{camera_id}/disconnect")
async def disconnect_camera(camera_id: int, db: Session = Depends(get_db)):
    """
    Tear down the camera session and its detection task.
    The stream_worker task will notice the frame_buffer slot is gone and exit.
    """
    session = camera_manager.get_by_camera_id(camera_id)
    if not session:
        raise HTTPException(status_code=404, detail="Camera not connected")

    session_id = session.session_id

    # Cancel detection task
    task = _detection_tasks.pop(session_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Clean up state
    detection_flags.remove(session_id)
    detection_cache.clear(session_id)

    # Disconnect camera (releases cv2 capture, removes from frame_buffer)
    await camera_manager.disconnect(session_id)

    # Update DB
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if cam:
        cam.status = "disconnected"
        cam.session_id = None
        db.commit()

    return {"message": "Camera disconnected", "session_id": session_id}


# ──────────────────────────────────────────────────────────────────────────────
# Detection toggle  (instant, no restart)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{camera_id}/detection/toggle")
async def toggle_detection(camera_id: int):
    """
    Flip the detection flag for this session.

    Effect is immediate: the detection_worker checks the flag at the top of
    every loop iteration (~30 ms), so it stops/starts within one cycle.
    No task restart, no queue flush, no camera restart.
    """
    session = camera_manager.get_by_camera_id(camera_id)
    if not session:
        raise HTTPException(status_code=404, detail="Camera not connected")

    new_state = detection_flags.toggle(session.session_id)
    action = "enabled" if new_state else "disabled"

    logger.info(f"[API] Detection {action}  camera={camera_id}")
    return {
        "camera_id": camera_id,
        "session_id": session.session_id,
        "detection_enabled": new_state,
        "message": f"Detection {action}",
    }


@router.post("/{camera_id}/detection/enable")
async def enable_detection(camera_id: int):
    session = camera_manager.get_by_camera_id(camera_id)
    if not session:
        raise HTTPException(status_code=404, detail="Camera not connected")
    detection_flags.enable(session.session_id)
    return {"detection_enabled": True}


@router.post("/{camera_id}/detection/disable")
async def disable_detection(camera_id: int):
    session = camera_manager.get_by_camera_id(camera_id)
    if not session:
        raise HTTPException(status_code=404, detail="Camera not connected")
    detection_flags.disable(session.session_id)
    return {"detection_enabled": False}


# ──────────────────────────────────────────────────────────────────────────────
# Detection status
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{camera_id}/detection/status")
async def detection_status(camera_id: int):
    """Return current toggle state and the latest cached detections."""
    session = camera_manager.get_by_camera_id(camera_id)
    if not session:
        raise HTTPException(status_code=404, detail="Camera not connected")

    sid = session.session_id
    enabled = detection_flags.is_enabled(sid)
    detections = detection_cache.get(sid)

    return {
        "camera_id": camera_id,
        "session_id": sid,
        "detection_enabled": enabled,
        "detection_count": len(detections),
        "detections": detections,
        "db_queue_depth": db_write_queue.qsize(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket video stream
# ──────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/stream/{session_id}")
async def websocket_stream(
    websocket: WebSocket,
    session_id: str,
    show_detections: bool = True,
):
    """
    Pure streaming endpoint.

    • Accepts the WebSocket.
    • Starts stream_worker as a task.
    • Waits for the client to disconnect or the task to finish.
    • On disconnect, cancels the task cleanly.

    The camera loop and detection worker are UNAFFECTED by this connection
    opening or closing.
    """
    await websocket.accept()

    # Verify session exists
    session = camera_manager.get(session_id)
    if session is None:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    task = asyncio.create_task(
        stream_worker(websocket, session_id, show_detections),
        name=f"stream-{session_id}",
    )

    try:
        # Keep the handler alive while the task runs.
        # If the client disconnects, WebSocketDisconnect is raised here.
        await asyncio.shield(task)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        logger.warning(f"[WS] stream/{session_id} error: {exc}")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info(f"[WS] stream/{session_id} closed")