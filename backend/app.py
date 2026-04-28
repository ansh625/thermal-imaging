from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, BackgroundTasks, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from typing import Optional, List, Dict
from fastapi import Query
from pydantic import BaseModel
import os
import uuid
import cv2
import asyncio
import base64
import secrets
import logging
from pathlib import Path
import json
import numpy as np
import time
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from database import SessionLocal 
from database import (get_db, init_db, User, Camera, Recording, Detection, 
                     RecordingSchedule, Notification)
from auth import (authenticate_user, create_access_token, get_current_active_user,
                  get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES)
from camera_handler import camera_manager
from yolo_detector import yolo_detector
from recording_manager import recording_manager
from notification_service import notification_service
from scheduler_service import scheduler_service
from email_service import email_service
from websocket_manager import websocket_manager
from collections import defaultdict 

app = FastAPI(title="CSIO ThermalStream API", version="2.0.0")

# ==================== DETECTION STATE MANAGER ====================

class CachedDetectionState:
    """Manages cached detections for smooth rendering"""
    def __init__(self):
        self.cached_detections: Dict[str, List[Dict]] = {}
        self.detection_ages: Dict[str, int] = {}
    
    def update(self, session_id: str, detections: List[Dict]):
        """Update cached detections"""
        self.cached_detections[session_id] = detections
        self.detection_ages[session_id] = 0
    
    def get(self, session_id: str) -> List[Dict]:
        """Get cached detections with aging"""
        if session_id not in self.cached_detections:
            return []
        
        # Age out old detections (if not updated in 3 frames, clear them)
        age = self.detection_ages.get(session_id, 0)
        if age > 3:
            self.cached_detections[session_id] = []
            return []
        
        self.detection_ages[session_id] = age + 1
        return self.cached_detections[session_id]
    
    def clear(self, session_id: str):
        """Clear detections for session"""
        if session_id in self.cached_detections:
            del self.cached_detections[session_id]
        if session_id in self.detection_ages:
            del self.detection_ages[session_id]

detection_cache = CachedDetectionState()

origins=[
        "http://localhost:5173"
        ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories first
for dir_path in ['recordings', 'screenshots', 'detections', 'thumbnails']:
    Path(dir_path).mkdir(exist_ok=True)

# Mount static files for detections and recordings
app.mount("/detections", StaticFiles(directory="detections"), name="detections")
app.mount("/recordings", StaticFiles(directory="recordings"), name="recordings")

# Storage tracking
storage_stats = {
    'recordings': 0,
    'screenshots': 0,
    'detections': 0,
    'total': 0
}

def calculate_storage():
    """Calculate total storage used"""
    global storage_stats
    total = 0
    for dir_name in ['recordings', 'screenshots', 'detections']:
        dir_size = sum(f.stat().st_size for f in Path(dir_name).rglob('*') if f.is_file())
        storage_stats[dir_name] = dir_size
        total += dir_size
    storage_stats['total'] = total

@app.on_event("startup")
async def startup():
    init_db()
    scheduler_service.reload_all_schedules()
    calculate_storage()
    print("✅ CSIO ThermalStream API Started")

# ==================== REQUEST MODELS ====================

class CameraConnectRequest(BaseModel):
    """Request model for camera connection"""
    url: str
    camera_id: int = 1
    stream_type: Optional[str] = None  # "usb", "rtsp", "ip", or "raw"

# ==================== AUTHENTICATION ====================

@app.post("/api/auth/signup")
async def signup(email: str, password: str, full_name: str, 
                organization: Optional[str] = None,
                db: Session = Depends(get_db)):
    """User signup"""
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        organization=organization,
        role="operator"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "message": "User created successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
               db: Session = Depends(get_db)):
    """User login"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organization": user.organization
        }
    }

@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organization": current_user.organization
    }

@app.post("/api/auth/forgot-password")
async def forgot_password(email: str, 
                         background_tasks: BackgroundTasks,
                         db: Session = Depends(get_db)):
    """Initiate password reset"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    # Try to send email synchronously with error handling
    logger.info(f"Attempting to send password reset email to {user.email}")
    try:
        email_sent = email_service.send_password_reset_email(user.email, reset_token)
        if email_sent:
            logger.info(f"Password reset email successfully sent to {user.email}")
            return {
                "message": "If the email exists, a reset link has been sent",
                "success": True
            }
        else:
            logger.warning(f"Failed to send password reset email to {user.email}")
            # Still return success message for security, but log the failure
            return {
                "message": "If the email exists, a reset link has been sent",
                "success": False,
                "note": "Email sending failed - token generated but not sent"
            }
    except Exception as e:
        logger.error(f"Exception while sending password reset email: {e}")
        return {
            "message": "If the email exists, a reset link has been sent",
            "success": False,
            "error": str(e)
        }

@app.post("/api/auth/reset-password")
async def reset_password(token: str, new_password: str,
                        db: Session = Depends(get_db)):
    """Reset password with token"""
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Password reset successful"}

@app.post("/api/auth/test-email")
async def test_email(to_email: str = "test@example.com"):
    """Test email sending - for debugging SMTP issues"""
    logger.info(f"Testing email sending to {to_email}")
    try:
        test_html = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>CSIO ThermalStream - Email Test</h2>
            <p>This is a test email to verify SMTP configuration is working correctly.</p>
            <p><strong>If you received this, email sending is working!</strong></p>
            <p style="color: #666; margin-top: 20px;">Test sent at: {}</p>
        </body>
        </html>
        """.format(datetime.utcnow().isoformat())
        
        result = email_service.send_email(to_email, "CSIO ThermalStream - Email Test", test_html)
        
        if result:
            logger.info(f"✓ Test email sent successfully to {to_email}")
            return {
                "success": True,
                "message": "Test email sent successfully",
                "email": to_email,
                "smtp_host": email_service.smtp_host,
                "smtp_port": email_service.smtp_port,
                "from_email": email_service.from_email
            }
        else:
            logger.error(f"✗ Test email failed to send to {to_email}")
            return {
                "success": False,
                "message": "Test email failed to send - check backend logs for details",
                "email": to_email
            }
    except Exception as e:
        logger.error(f"✗ Exception during email test: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "error_type": type(e).__name__
        }

@app.get("/api/auth/forgot-password-code")
async def get_forgot_password_code(email: str, 
                                    db: Session = Depends(get_db)):
    """
    ALTERNATIVE METHOD: Get password reset code (without email)
    Returns a reset token that can be used to reset password
    Useful when email is not working
    """
    try:
        logger.info(f"Reset code requested for email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Reset code requested for non-existent user: {email}")
            return {
                "message": "If the email exists, a reset code has been generated",
                "success": False
            }
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # Return the code directly to user (for alternative workflow)
        logger.info(f"✓ Reset code generated for {user.email}")
        logger.warning(f"PASSWORD RESET CODE FOR {user.email}: {reset_token}")
        
        return {
            "success": True,
            "message": "Reset code generated successfully",
            "reset_token": reset_token,
            "expires_in": "1 hour",
            "note": "Use this token at /reset-password endpoint with the new password"
        }
    except Exception as e:
        logger.error(f"✗ Error generating reset code for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating reset code: {str(e)}")

# ==================== USER PROFILE & SECURITY ====================

# Pydantic models for user endpoints
class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@app.put("/api/users/update-profile")
async def update_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile information (name, organization)"""
    try:
        if profile_data.full_name:
            current_user.full_name = profile_data.full_name
        if profile_data.organization is not None:
            current_user.organization = profile_data.organization
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "organization": current_user.organization,
            "role": current_user.role
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating profile for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@app.post("/api/users/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password (requires old password verification)"""
    try:
        # Verify old password
        if not verify_password(password_data.old_password, current_user.hashed_password):
            raise HTTPException(status_code=401, detail="Old password is incorrect")
        
        # Update with new password hash
        current_user.hashed_password = get_password_hash(password_data.new_password)
        db.commit()
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")

# ==================== CAMERA MANAGEMENT ====================

@app.post("/api/camera/connect")
async def connect_camera(url: str, camera_id: int = 1, stream_type: Optional[str] = None,
                        current_user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    """Connect to camera with optional stream type specification"""
    
    # Validate stream type if provided
    valid_types = ["usb", "rtsp", "ip", "raw"]
    if stream_type and stream_type.lower() not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid stream_type. Must be one of: {', '.join(valid_types)}"
        )
    
    session_id = str(uuid.uuid4())
    session = await camera_manager.create_session(session_id, url, camera_id, stream_type)
    
    if not session:
        # Provide stream-specific error guidance
        stream_lower = (stream_type or "unknown").lower()
        
        if stream_lower == "usb":
            detail = "USB camera not found. Check: (1) Device index (usually 0, 1, or 2), (2) Camera is connected, (3) No other application is using the camera"
        elif stream_lower == "rtsp":
            detail = "RTSP connection failed. Check: (1) IP address is correct, (2) Camera is on the network, (3) RTSP stream path is correct (common: /stream, /main, /ch0, /preview), (4) Firewall allows RTSP (port 554)"
        elif stream_lower == "ip":
            detail = "IP camera connection failed. Check: (1) IP address or hostname is correct, (2) Camera is accessible on the network, (3) Camera's web interface works, (4) Correct HTTP/HTTPS port"
        elif stream_lower == "raw":
            detail = "Raw stream connection failed. Check: (1) Stream URL is complete and correct, (2) URL includes protocol (http://, https://, rtsp://), (3) Network connectivity to stream source"
        else:
            detail = "Failed to connect to camera. Check the URL format and ensure the camera/stream is accessible on the network"
        
        raise HTTPException(status_code=400, detail=detail)
    
    # Determine connection type for database
    connection_type = stream_type or session.stream_type
    
    # Update or create camera in database
    camera = db.query(Camera).filter(
        Camera.user_id == current_user.id,
        Camera.connection_url == url
    ).first()
    
    if not camera:
        camera = Camera(
            name=f"Camera {camera_id} ({connection_type.upper()})",
            connection_type=connection_type,
            connection_url=url,
            user_id=current_user.id
        )
        db.add(camera)
    else:
        camera.name = f"Camera {camera_id} ({connection_type.upper()})"
        camera.connection_type = connection_type
    
    camera.status = "connected"
    camera.session_id = session_id
    camera.fps = session.fps
    camera.last_seen = datetime.utcnow()
    camera.resolution = "1280x720"
    db.commit()
    db.refresh(camera)
    
    # Send notification
    notification_service.create_notification(
        user_id=current_user.id,
        title="Camera Connected",
        message=f"Camera {camera.name} connected successfully",
        type="success",
        data={"camera_id": camera.id, "session_id": session_id}
    )
    
    # Broadcast to user via WebSocket
    await websocket_manager.broadcast_to_user(
        current_user.id,
        "camera_connected",
        {
            "camera_id": camera.id,
            "session_id": session_id,
            "name": camera.name,
            "stream_type": connection_type,
            "fps": session.fps
        }
    )
    
    return {
        "session_id": session_id,
        "camera_id": camera.id,
        "stream_type": connection_type,
        "fps": session.fps,
        "resolution": "1280x720",
        "status": "connected"
    }

@app.post("/api/camera/disconnect")
async def disconnect_camera(session_id: str,
                           current_user: User = Depends(get_current_active_user),
                           db: Session = Depends(get_db)):
    """Disconnect camera"""
    # Stop recording if active
    if recording_manager.is_recording(session_id):
        await stop_recording(session_id, current_user, db)
    
    await camera_manager.disconnect_session(session_id)
    
    # Update camera status
    camera = db.query(Camera).filter(
        Camera.session_id == session_id,
        Camera.user_id == current_user.id
    ).first()
    
    if camera:
        camera.status = "disconnected"
        camera.session_id = None
        db.commit()
        
        # Send notification
        notification_service.create_notification(
            user_id=current_user.id,
            title="Camera Disconnected",
            message=f"Camera {camera.name} disconnected",
            type="info",
            data={"camera_id": camera.id}
        )
        
        # Broadcast
        await websocket_manager.broadcast_to_user(
            current_user.id,
            "camera_disconnected",
            {"camera_id": camera.id}
        )
    
    return {"message": "Camera disconnected"}

@app.get("/api/camera/list")
async def list_cameras(current_user: User = Depends(get_current_active_user),
                      db: Session = Depends(get_db)):
    """Get all user cameras"""
    cameras = db.query(Camera).filter(Camera.user_id == current_user.id).all()
    return {
        "cameras": [
            {
                "id": cam.id,
                "name": cam.name,
                "connection_type": cam.connection_type,
                "connection_url": cam.connection_url,
                "status": cam.status,
                "fps": cam.fps,
                "resolution": cam.resolution,
                "last_seen": cam.last_seen,
                "session_id": cam.session_id
            }
            for cam in cameras
        ]
    }

@app.delete("/api/camera/{camera_id}")
async def delete_camera(camera_id: int,
                       current_user: User = Depends(get_current_active_user),
                       db: Session = Depends(get_db)):
    """Delete camera"""
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.user_id == current_user.id
    ).first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Disconnect if connected
    if camera.session_id:
        await camera_manager.disconnect_session(camera.session_id)
    
    db.delete(camera)
    db.commit()
    
    return {"message": "Camera deleted"}

# ==================== VIDEO STREAMING ====================

@app.websocket("/ws/video/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket video streaming - optimized for fast startup"""
    try:
        await websocket.accept()
        
        detection_enabled = True  # Enable detection by default
        detection_confidence = 0.5
        db = next(get_db())
        frame_count = 0
        scheduled_recording_active = False
        
        # Get camera session with fast fail
        camera_session = camera_manager.get_session(session_id)
        if not camera_session or not camera_session.connected:
            await websocket.close(code=1008, reason="Camera not connected")
            return
        
        # Get camera from database
        camera = db.query(Camera).filter(Camera.session_id == session_id).first()
        if not camera:
            await websocket.close(code=1008, reason="Camera not found")
            return
        
        logger.info(f"WebSocket stream started for camera {camera.id} (session: {session_id})")
        
        # Check if there's an active scheduled recording for this camera
        active_schedule = scheduler_service.get_active_schedule(camera.id)
        if active_schedule:
            logger.info(f"Active scheduled recording detected for camera {camera.id}")
            # Start recording automatically from schedule
            filepath = recording_manager.start_recording(
                session_id,
                camera_session.fps,
                (1280, 720),
                camera.name
            )
            if filepath:
                # Create database entry for scheduled recording
                recording = Recording(
                    filename=os.path.basename(filepath),
                    format="mp4",
                    storage_path=filepath,
                    camera_id=camera.id,
                    user_id=camera.owner.id,
                    started_at=datetime.utcnow(),
                    is_scheduled=True  # Mark as scheduled
                )
                db.add(recording)
                db.commit()
                scheduled_recording_active = True
                logger.info(f"Scheduled recording started for camera {camera.id}")
        
        # Send immediate "ready" message
        await websocket.send_json({
            "type": "stream_ready",
            "fps": camera_session.fps,
            "resolution": "1280x720"
        })
        
        DETECTION_INTERVAL = 3  # Run detection every 3 frames
        frame_skip_count = 0
        
        try:
            while camera_session.is_running and camera_session.connected:
                # Non-blocking check for client messages
                try:
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=0.001)
                    if message.get('type') == 'toggle_detection':
                        detection_enabled = message.get('enabled', False)
                        detection_confidence = message.get('confidence', 0.5)
                        if not detection_enabled:
                            detection_cache.clear(session_id)
                        logger.info(f"Detection {'enabled' if detection_enabled else 'disabled'}")
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.warning(f"Error receiving message: {e}")
                    break
                
                # Get frame
                frame = await camera_session.get_frame()
                if frame is None:
                    await asyncio.sleep(0.001)
                    continue
                
                frame_count += 1
                frame_skip_count += 1
                
                # Make a copy for recording (with detections drawn on it)
                recording_frame = frame.copy()
                
                # Minimal processing - only encode and send
                try:
                    # JPEG encoding with lower quality for speed
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # Prepare message
                    message = {
                        "frame": frame_base64,
                        "fps": camera_session.fps,
                        "timestamp": time.time()
                    }
                    
                    # YOLO Detection - run every N frames to avoid blocking
                    if detection_enabled and frame_skip_count % DETECTION_INTERVAL == 0:
                        try:
                            detections = yolo_detector.detect(frame, detection_confidence)
                            if detections:
                                detection_cache.update(session_id, detections)
                                message["detections"] = len(detections)
                                message["detection_data"] = detections  # Send full detection data
                                
                                # Async database write
                                loop = asyncio.get_event_loop()
                                loop.run_in_executor(
                                    None,
                                    lambda: _save_detections_sync(camera.id, detections, frame)
                                )
                        except Exception as e:
                            logger.error(f"Detection error: {e}")
                    
                    # Get cached detections
                    cached = detection_cache.get(session_id)
                    if cached:
                        message["cached_detections"] = len(cached)
                        message["cached_detection_data"] = cached  # Send cached detection data
                    
                    # Draw cached detections on recording frame
                    if cached:
                        recording_frame = yolo_detector.draw_detections(recording_frame, cached)
                    
                    # Write to recording if active
                    if recording_manager.is_recording(session_id):
                        recording_manager.write_frame(session_id, recording_frame)
                    
                    # Send frame
                    await websocket.send_json(message)
                    
                except Exception as e:
                    logger.error(f"Error encoding/sending frame: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            logger.info(f"WebSocket stream ended for camera {camera.id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

async def video_stream(websocket: WebSocket, session_id: str):
    """Alias for websocket_endpoint - maintained for backward compatibility"""
    await websocket_endpoint(websocket, session_id)


def _save_detections_sync(camera_id: int, detections, frame):
    """
    This runs in a background thread.
    It MUST create its own DB session.
    
    Args:
        camera_id: Camera ID for the detection
        detections: List of detection dictionaries from YOLO detector
        frame: The frame where detections were found (for saving detected objects)
    """

    db: Session = SessionLocal()

    try:
        for det in detections:
            # Extract detections from YOLO format
            bbox = det.get("bbox", {})
            
            # Save detection screenshot (cropped image of detected object)
            screenshot_path = None
            try:
                screenshot_path = yolo_detector.save_detection(frame, det, output_dir="detections")
                logger.debug(f"Saved detection screenshot: {screenshot_path}")
            except Exception as e:
                logger.warning(f"Failed to save detection screenshot: {e}")
            
            detection = Detection(
                camera_id=camera_id,
                class_name=det.get("class_name", "unknown"),
                confidence=det.get("confidence", 0.0),
                bbox_x1=bbox.get("x1", 0),
                bbox_y1=bbox.get("y1", 0),
                bbox_x2=bbox.get("x2", 0),
                bbox_y2=bbox.get("y2", 0),
                screenshot_path=screenshot_path,
                detected_at=datetime.utcnow()
            )
            db.add(detection)

        db.commit()
        logger.info(f"Successfully saved {len(detections)} detections for camera {camera_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error committing detections: {e}")

    finally:
        db.close()

# ==================== RECORDING MANAGEMENT ====================

@app.post("/api/recording/start")
async def start_recording(session_id: str,
                         schedule_id: Optional[int] = None,
                         current_user: User = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    """Start recording"""
    camera_session = camera_manager.get_session(session_id)
    if not camera_session:
        raise HTTPException(status_code=404, detail="Camera session not found")
    
    camera = db.query(Camera).filter(
        Camera.session_id == session_id,
        Camera.user_id == current_user.id
    ).first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Start recording
    filepath = recording_manager.start_recording(
        session_id,
        camera_session.fps,
        (1280, 720),
        camera.name
    )
    
    if not filepath:
        raise HTTPException(status_code=500, detail="Failed to start recording")
    
    # Create database entry
    recording = Recording(
        filename=os.path.basename(filepath),
        format="mp4",
        storage_path=filepath,
        camera_id=camera.id,
        user_id=current_user.id,
        started_at=datetime.utcnow(),
        is_scheduled=(schedule_id is not None)  # Mark as scheduled if schedule_id provided
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    
    # Notification
    notification_service.create_notification(
        user_id=current_user.id,
        title="Recording Started",
        message=f"Recording started for {camera.name}" + (" (Scheduled)" if schedule_id else ""),
        type="info",
        data={"recording_id": recording.id, "camera_id": camera.id, "schedule_id": schedule_id}
    )
    
    # Broadcast
    await websocket_manager.broadcast_to_user(
        current_user.id,
        "recording_started",
        {"recording_id": recording.id, "camera_id": camera.id, "schedule_id": schedule_id}
    )
    
    return {
        "recording_id": recording.id,
        "filename": recording.filename,
        "started_at": recording.started_at,
        "is_scheduled": recording.is_scheduled
    }

@app.post("/api/recording/stop")
async def stop_recording(session_id: str,
                        current_user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    """Stop recording"""
    stats = recording_manager.stop_recording(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="No active recording")
    
    # Update database
    recording = db.query(Recording).filter(
        Recording.filename == stats['filename'],
        Recording.user_id == current_user.id
    ).first()
    
    if recording:
        recording.duration_seconds = stats['duration_seconds']
        recording.file_size_bytes = stats['file_size_bytes']
        recording.ended_at = stats['ended_at']
        db.commit()
        
        # Update storage stats
        calculate_storage()
        
        # Notification
        notification_service.create_notification(
            user_id=current_user.id,
            title="Recording Stopped",
            message=f"Recording saved: {recording.filename}",
            type="success",
            data={"recording_id": recording.id}
        )
        
        # Broadcast
        await websocket_manager.broadcast_to_user(
            current_user.id,
            "recording_stopped",
            {"recording_id": recording.id, "duration": stats['duration_seconds']}
        )
    
    return {
        "message": "Recording stopped",
        "filename": stats['filename'],
        "duration_seconds": stats['duration_seconds'],
        "file_size_bytes": stats['file_size_bytes']
    }

@app.get("/api/recording/list")
async def list_recordings(current_user: User = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    """Get all recordings"""
    recordings = db.query(Recording).filter(
        Recording.user_id == current_user.id
    ).order_by(Recording.created_at.desc()).all()
    
    return {
        "recordings": [
            {
                "id": rec.id,
                "filename": rec.filename,
                "format": rec.format,
                "duration_seconds": rec.duration_seconds,
                "file_size_bytes": rec.file_size_bytes,
                "camera_id": rec.camera_id,
                "started_at": rec.started_at,
                "ended_at": rec.ended_at,
                "is_scheduled": rec.is_scheduled
            }
            for rec in recordings
        ]
    }

@app.get("/api/recording/download/{recording_id}")
async def download_recording(recording_id: int,
                            current_user: User = Depends(get_current_active_user),
                            db: Session = Depends(get_db)):
    """Download recording"""
    recording = db.query(Recording).filter(
        Recording.id == recording_id,
        Recording.user_id == current_user.id
    ).first()
    
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if not os.path.exists(recording.storage_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    def iterfile():
        with open(recording.storage_path, mode="rb") as file_like:
            yield from file_like
    
    return StreamingResponse(
        iterfile(),
        media_type='video/mp4',
        headers={
            'Content-Disposition': f'attachment; filename="{recording.filename}"',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    )

@app.delete("/api/recording/{recording_id}")
async def delete_recording(recording_id: int,
                          current_user: User = Depends(get_current_active_user),
                          db: Session = Depends(get_db)):
    """Delete recording"""
    recording = db.query(Recording).filter(
        Recording.id == recording_id,
        Recording.user_id == current_user.id
    ).first()
    
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # Delete file
    if os.path.exists(recording.storage_path):
        os.remove(recording.storage_path)
    
    db.delete(recording)
    db.commit()
    
    calculate_storage()
    
    return {"message": "Recording deleted"}

# ==================== DETECTION MANAGEMENT ====================

@app.get("/api/detection/list")
async def list_detections(limit: int = 100,
                         current_user: User = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    """Get detection history"""
    detections = db.query(Detection).join(Camera).filter(
        Camera.user_id == current_user.id
    ).order_by(Detection.detected_at.desc()).limit(limit).all()
    
    return {
        "detections": [
            {
                "id": det.id,
                "class_name": det.class_name,
                "confidence": det.confidence,
                "bbox": {
                    "x1": det.bbox_x1,
                    "y1": det.bbox_y1,
                    "x2": det.bbox_x2,
                    "y2": det.bbox_y2
                },
                "screenshot_path": det.screenshot_path,
                "camera_id": det.camera_id,
                "detected_at": det.detected_at
            }
            for det in detections
        ]
    }

# ==================== SCREENSHOT ====================

@app.post("/api/screenshot/capture")
async def capture_screenshot(session_id: str,
                            current_user: User = Depends(get_current_active_user),
                            db: Session = Depends(get_db)):
    """Capture and save a screenshot from live stream"""
    camera_session = camera_manager.get_session(session_id)
    if not camera_session:
        raise HTTPException(status_code=404, detail="Camera session not found")
    
    camera = db.query(Camera).filter(
        Camera.session_id == session_id,
        Camera.user_id == current_user.id
    ).first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Get latest frame from camera session
    frame = camera_session.last_frame
    if frame is None:
        raise HTTPException(status_code=400, detail="No frame available")
    
    # Save screenshot
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        screenshot_dir = "screenshots"
        Path(screenshot_dir).mkdir(exist_ok=True)
        
        filename = f"{camera.name}_{timestamp}.jpg"
        filepath = os.path.join(screenshot_dir, filename)
        
        # Run YOLO detection and draw bounding boxes on the screenshot
        screenshot_frame = frame.copy()
        try:
            detections = yolo_detector.detect(frame, confidence=0.5)
            if detections:
                screenshot_frame = yolo_detector.draw_detections(screenshot_frame, detections)
                logger.debug(f"Detected {len(detections)} objects in screenshot")
        except Exception as e:
            logger.warning(f"Failed to run detection on screenshot: {e}")
        
        cv2.imwrite(filepath, screenshot_frame)
        
        logger.info(f"Screenshot saved: {filepath}")
        
        # Broadcast notification
        await websocket_manager.broadcast_to_user(
            current_user.id,
            "screenshot_taken",
            {"filename": filename, "path": filepath, "camera_id": camera.id}
        )
        
        return {
            "message": "Screenshot captured successfully",
            "filename": filename,
            "path": filepath
        }
        
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")
        raise HTTPException(status_code=500, detail="Failed to capture screenshot")

# ==================== SCHEDULER ====================

@app.post("/api/schedule/create")
async def create_schedule(camera_id: int = Query(...),
                         name: str = Query(...),
                         days_of_week: List[str] = Query(...),
                         start_time: str = Query(...),
                         end_time: str = Query(...),
                         current_user: User = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    """Create recording schedule"""
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.user_id == current_user.id
    ).first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    schedule = RecordingSchedule(
        camera_id=camera_id,
        name=name,
        days_of_week=days_of_week,
        start_time=start_time,
        end_time=end_time,
        enabled=True
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    # Add to scheduler
    scheduler_service.add_schedule(schedule.id)
    
    notification_service.create_notification(
        user_id=current_user.id,
        title="Schedule Created",
        message=f"Recording schedule '{name}' created",
        type="success",
        data={"schedule_id": schedule.id}
    )
    
    return {
        "id": schedule.id,
        "name": schedule.name,
        "days_of_week": schedule.days_of_week,
        "start_time": schedule.start_time,
        "end_time": schedule.end_time,
        "enabled": schedule.enabled
    }

@app.get("/api/schedule/list")
async def list_schedules(current_user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    """Get all schedules"""
    schedules = db.query(RecordingSchedule).join(Camera).filter(
        Camera.user_id == current_user.id
    ).all()
    
    return {
        "schedules": [
            {
                "id": sch.id,
                "camera_id": sch.camera_id,
                "name": sch.name,
                "days_of_week": sch.days_of_week,
                "start_time": sch.start_time,
                "end_time": sch.end_time,
                "enabled": sch.enabled
            }
            for sch in schedules
        ]
    }

@app.put("/api/schedule/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int,
                         current_user: User = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    """Enable/disable schedule"""
    schedule = db.query(RecordingSchedule).join(Camera).filter(
        RecordingSchedule.id == schedule_id,
        Camera.user_id == current_user.id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.enabled = not schedule.enabled
    db.commit()
    
    if schedule.enabled:
        scheduler_service.add_schedule(schedule.id)
    else:
        scheduler_service.remove_schedule(schedule.id)
    
    return {"enabled": schedule.enabled}

@app.delete("/api/schedule/{schedule_id}")
async def delete_schedule(schedule_id: int,
                         current_user: User = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    """Delete schedule"""
    schedule = db.query(RecordingSchedule).join(Camera).filter(
        RecordingSchedule.id == schedule_id,
        Camera.user_id == current_user.id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    scheduler_service.remove_schedule(schedule.id)
    db.delete(schedule)
    db.commit()
    
    return {"message": "Schedule deleted"}

# ==================== NOTIFICATIONS ====================

@app.get("/api/notifications")
async def get_notifications(unread_only: bool = False,
                           current_user: User = Depends(get_current_active_user)):
    """Get user notifications"""
    notifications = notification_service.get_user_notifications(
        current_user.id,
        unread_only=unread_only
    )
    
    return {
        "notifications": [
            {
                "id": notif.id,
                "title": notif.title,
                "message": notif.message,
                "type": notif.type,
                "is_read": notif.is_read,
                "data": notif.data,
                "created_at": notif.created_at
            }
            for notif in notifications
        ]
    }

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int,
                                current_user: User = Depends(get_current_active_user)):
    """Mark notification as read"""
    success = notification_service.mark_as_read(notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}

@app.put("/api/notifications/read-all")
async def mark_all_read(current_user: User = Depends(get_current_active_user)):
    """Mark all notifications as read"""
    notification_service.mark_all_as_read(current_user.id)
    return {"message": "All marked as read"}

# ==================== DASHBOARD STATS ====================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_active_user),
                             db: Session = Depends(get_db)):
    """Get real-time dashboard statistics"""
    # Active cameras
    active_cameras = db.query(Camera).filter(
        Camera.user_id == current_user.id,
        Camera.status == "connected"
    ).count()
    
    # Total recordings
    total_recordings = db.query(Recording).filter(
        Recording.user_id == current_user.id
    ).count()
    
    # Total detections
    total_detections = db.query(Detection).join(Camera).filter(
        Camera.user_id == current_user.id
    ).count()
    
    # Calculate storage
    calculate_storage()
    storage_gb = round(storage_stats['total'] / (1024**3), 2)
    
    return {
        "active_cameras": active_cameras,
        "total_recordings": total_recordings,
        "total_detections": total_detections,
        "storage_used_gb": storage_gb,
        "storage_breakdown": {
            "recordings_gb": round(storage_stats['recordings'] / (1024**3), 2),
            "screenshots_gb": round(storage_stats['screenshots'] / (1024**3), 2),
            "detections_gb": round(storage_stats['detections'] / (1024**3), 2)
        }
    }

# ==================== REAL-TIME UPDATES ====================

@app.websocket("/ws/updates/{user_id}")
async def realtime_updates(websocket: WebSocket, user_id: int):
    """WebSocket for real-time dashboard updates"""
    await websocket_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, user_id)

# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    return {
        "app": "CSIO ThermalStream API",
        "version": "2.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "yolo_loaded": yolo_detector.is_loaded,
        "active_cameras": len(camera_manager.sessions),
        "active_recordings": len(recording_manager.active_recordings)
    }


#========================= ADVANCED ANALYTICS ====================

@app.get("/api/analytics/advanced")
async def get_advanced_analytics(
    date_from: Optional[str] = Query(None, description= "Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description = "End date YYYY-MM-DD"),
    class_names: Optional[List[str]] = Query(None, description="Filter by object class"),
    camera_ids: Optional[List[int]] = Query(None, description="Filter by camera IDs"),  
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
    
):
    """
    Advanced analytics with filtering, aggregation, zone analysis,
    activity heatmap, trend comparison, and smart insights.
    All queries are scoped to the current user's cameras.
    """
    
    # ______________ Base query scoped to current user's cameras_______________________________
    #all detections from cameras belonging to current user
    
    base_q = (
        db.query(Detection)
        .join(Camera)
        .filter(Camera.user_id == current_user.id)
    )

# ----------------------Apply filters ------------------------
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            base_q = base_q.filter(Detection.detected_at >= dt_from)
        except ValueError:
            raise HTTPException(status_code=400, detail= "Invalid date_from. Use YYYY-MM-DD format.")

    if date_to:
        try:
            #include the full end day up to 23:59:59
            dt_to = datetime.fromisoformat(date_to+"T23:59:59")
            base_q = base_q.filter(Detection.detected_at <= dt_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to. Use YYYY-MM-DD format.")
        
    if class_names:
        base_q = base_q.filter(Detection.class_name.in_(class_names))
    
    if camera_ids:
        base_q = base_q.filter(Camera.id.in_(camera_ids))
        
        
# Fetch all matching detections ordered by time (needed for gap analysis)
    all_detections = base_q.order_by(Detection.detected_at.asc()).all()
    total = len(all_detections)
    
    
    #___________________ Single-pass aggregation __________________________________ 
    
    by_class: dict = defaultdict(int)
    by_date: dict = defaultdict(int)
    by_camera_meta: dict = defaultdict(lambda: {"count": 0, "name": "", "confs": []})
    hour_counts: dict = defaultdict(int)
    activity_grid: dict = defaultdict(int)    # key: (hour 0-23, weekday 0=Mon)
    hourly_buckets: dict= defaultdict(int) # key: "YYYY-MM-DD HH:00"
    
    for det in all_detections: 
        by_class[det.class_name] += 1
        by_date[det.detected_at.strftime("%Y-%m-%d")] += 1
        by_camera_meta[det.camera_id]["count"] += 1
        by_camera_meta[det.camera_id]["name"] = (
            det.camera.name if det.camera else f"Camera {det.camera_id}"
        )
        by_camera_meta[det.camera_id]["confs"].append(det.confidence)
        hour_counts[det.detected_at.hour] += 1
        activity_grid[(det.detected_at.hour, det.detected_at.weekday())] += 1 
        hourly_buckets[det.detected_at.strftime("%Y-%m-%d %H:00")] += 1
        
        by_date_sorted = [{"date": k, "count": v} for k, v in sorted(by_date.items())]
        
        
    #_________ 1. Detection Count Analytics ___________________________
    
    detection_counts = {
        "total": total,
        "by_class": [
            {
                "class_name": k,
                "count": v,
                "percentage": round(v / total * 100, 1) if total > 0 else 0
            }
            for k, v in sorted(by_class.items(), key=lambda x: x[1], reverse=True)
        ],
        "by_date": by_date_sorted
    }
    
    
    #___________ 2. Activity Intensity Heatmap (24 hours * 7 weekdays)____________________
    activity_intensity = [
        {"hour": h, "weekday": w, "count": activity_grid.get((h,w), 0)}
        for h in range(24)
        for w in range(7)
    ]
    
    
    #______ 3. Peak hours (sorted top 10)_____________________________
    
    peak_hours = sorted(
        [
            {"hour": h, "count": c, "label": f"{h:02d}:00"}
            for h,c in hour_counts.items()
        ],
        key=lambda x:x["count"],
        reverse= True
    )[:10]
    
    
    
    #__________4. Zone analytics (3*3 grid assuming 1280*720 frame) _____________________
    # zones mapped to (row,col) where row 0=top, col 0=left
    
    FRAME_W, FRAME_H = 1280, 720
    ZONE_NAMES = {
        (0,0): "Top-Left",
        (0,1): "Top-Center",
        (0,2): "Top-Right",
        (1,0): "Mid-Left",
        (1,1): "Mid-Center",
        (1,2): "Mid-Right",
        (2,0): "Bot-Left",
        (2,1): "Bot-Center",
        (2,2): "Bot-Right"
    }
    zone_counts: dict = defaultdict(int)
    for day in all_detections:
        cx = (det.bbox_x1 + det.bbox_x2) / 2
        cy = (det.bbox_y1 + det.bbox_y2) / 2
        col = min(int(cx / FRAME_W * 3), 2)
        row = min(int(cy / FRAME_H * 3), 2)
        zone_counts[ZONE_NAMES[(row, col)]] += 1
    zone_analytics = [
        {"zone": name, "count": zone_counts.get(name, 0)}
        for name in ZONE_NAMES.values()
    ]
    
    
#__________5. Object-wise analysis ________________________

    today_d = datetime.now(timezone.utc).date()
    yesterday_d = today_d - timedelta(days=1)
    object_analytics = []
    for cls, count in sorted(by_class.items(), key=lambda x: x[1], reverse=True):
        cls_dets = [d for d in all_detections if d.class_name == cls]
        confs = [d.confidence for d in cls_dets]
        avg_conf = sum(confs) / len(confs) if confs else 0
        today_c = sum(1 for d in cls_dets if d.detected_at.date() == today_d)
        yest_c = sum(1 for d in cls_dets if d.detected_at.date() == yesterday_d)
        
        object_analytics.append({
            "class_name" : cls,
            "count" : count, 
            "percentage" : round(count / total * 100, 1) if total > 0 else 0,
            "avg_confidence" : round(avg_conf * 100, 1),
            "max_confidence" : round(max(confs) * 100, 1) if confs else 0,
            "today_count" : today_c,
            "yesterday_count" : yest_c,
            "trand_pct" : round(((today_c - yest_c) / max(yest_c, 1)) * 100, 1)
        })

#__________6. Alert analytics (confidence >= 0.8, no separate model needed)____________

    ALERT_THRESHOLD = 0.8
    high_conf = [d for d in all_detections if d.confidence >= ALERT_THRESHOLD]
    alert_by_class: dict = defaultdict(int)
    for d in high_conf:
        alert_by_class[d.class_name] += 1
    alert_analytics = {
        "total_alerts" : len(high_conf),
        "threshold" : ALERT_THRESHOLD,
        "by_class" : [
            {"class_name": k, "count" : v}
            for k,v in sorted(alert_by_class.items(), key= lambda x : x[1], reverse=True)
        ],
        "alert_rate_pct" : round(len(high_conf) / total * 100, 1) if total > 0 else 0
        
    }
    
#_________ 7. Camera-wise analytics __________________________

    camera_analytics = []
    for cam_id, meta in by_camera_meta.items():
        confs = meta["confs"]
        cam_dets = [d for d in all_detections if d.camera_id == cam_id]
        last_ts = cam_dets[-1].detected_at if cam_dets else None
        camera_analytics.append({
            "camera_id" : cam_id,
            "camera_name" : meta["name"],
            "count" : meta["count"],
            "avg_comfidence" : round(sum(confs) / len(confs) * 100, 1) if confs else 0,
            "last_detection" : last_ts.strftime("%Y-%m-%d %H:%M") if last_ts else None
        })
    camera_analytics.sort(key=lambda x: x["count"], reverse=True)
        
#__________ 8. Trend analytics(today vs yesterday, this week vs last week) _____________
    week_start = today_d - timedelta(days=today_d.weekday())
    last_week_start = week_start - timedelta(days=7)
    today_count = sum(1 for d in all_detections if d.detected_at.date() == today_d)
    yest_count = sum(1 for d in all_detections if d.detected_at.date() == yesterday_d)
    this_week = sum(1 for d in all_detections if d.detected_at.date() >= week_start) 
    last_week = sum(1 for d in all_detections if d.detected_at.date() >= last_week_start and d.detected_at.date() < week_start)
    last_week = sum(
        1 for d in all_detections
        if last_week_start <= d.detected_at.date()< week_start
    )
    trend_analytics = {
        "today_count": today_count,
        "yesterday_count": yest_count,
        "day_change_pct" : round(((today_count - yest_count) / max(yest_count, 1)) * 100, 1),
        "this_week" : this_week, 
        "last_week" : last_week,
        "week_change_pct" : round(((this_week - last_week) / max(last_week, 1)) * 100, 1),
        "daily_series" : by_date_sorted[-30:] # last 30 days
    } 
    
#________ 9. Average detection rate _________________________

    if total > 1:
        span_hours = max(
            (all_detections[-1].detected_at - all_detections[0].detected_at).total_seconds()/3600,
            1.0
        )
        avg_rate = round(total / span_hours, 2)
    else: 
        avg_rate = float(total)
        
#____________10. No-activity periods (consecutive gaps >= 30 minutes)______________________________
    GAP_THRESHOLD_MINUTES = 30
    no_activity_periods = []
    if len(all_detections) > 1:
        for i in range(1, len(all_detections)):
            gap_min = (
                all_detections[i].detected_at  - all_detections[i-1].detected_at
            ).total_seconds() / 60
            if gap_min >= GAP_THRESHOLD_MINUTES:
                no_activity_periods.append({
                    "from": all_detections[i-1].detected_at.strftime("%Y-%m-%d %H:%M"),
                    "to": all_detections[i].detected_at.strftime("%Y-%m-%d %H:%M"),
                    "duration_minutes": round(gap_min, 1)
                })
    no_activity_periods.sort(key=lambda x: x["duration_minutes"], reverse=True)


# ___ 11. Timeline chart (houly buckets for graph plotting)___________________________

    timeline_chart = [
        {"time": k, "count": v}
        for k, v in sorted(hourly_buckets.items())
    ]
    
#____ 12. Smart insights (auto-generated)_________________________

    insights = []
    if total == 0:
        insights.append({
            "type": "info",
            "text": "No detections found for the selected filters."
        })
    else:
        #Most detected class
        if by_class:
            top_cls = max(by_class, key=by_class.get)
            pct = round(by_class[top_cls] / total * 100, 1)
            insights.append({
                "type": "info",
                "text": f"'{top_cls.capitalize()}' is the most detected object - {by_class[top_cls]} detections ({pct}% of total activity)."
            })
        
        #Peak hours
        if peak_hours:
            ph = peak_hours[0]
            insights.append({
                "type": "info",
                "text": f"Peak detection hour is {ph['label']} with {ph['count']} detections."
            })
            
        # Day-over-day trend 
        
        if yest_count > 0:
            if today_count > yest_count:
                direction = "up"
                w = "warning"
            elif today_count < yest_count:
                direction = "down"
                w = "success"
            else:
                direction = "unchanged"
                t = "info"
            pct = round(abs(trend_analytics["day_change_pct"]))
            
            if direction == "unchanged":
                insights.append({
                 "type": t,
                 "text": f"Activity remained unchanged compared to yesterday ({today_count} detections)."
            })
            else:
                insights.append({
                 "type": w,
                 "text": f" Activity is {direction} {pct}% today vs yesterday ({today_count} vs {yest_count} detections)"
            })
        
        elif today_count > 0:
            insights.append({
                "type": "info",
                "text": f"{today_count} new detections recorded today (no data for yesterday to compare)"
            })
            
        # High confidence alerts 
        if len(high_conf) > 0:
            insights.append({
                "type": "warning",
                "text": f"{len(high_conf)} high-confidence alerts detected (>= {int(ALERT_THRESHOLD*100)}% confidence). Review these events."
            })    

        # Longest quiet period
        if no_activity_periods:
            lg = no_activity_periods[0]
            insights.append({
                "type": "info",
                "text": f"Longest quiet gap: {lg['duration_minutes']} min (from{lg['from']} to {lg['to']})."
            })
    
        # Most active camera
        if camera_analytics:
            top_cam = camera_analytics[0]
            insights.append({
                "type": "info",
                "text": f"Most active camera is '{top_cam['camera_name']} with {top_cam['count']} detections."
            })

        # Busiest Zone
        if zone_counts:
            top_zone = max(zone_counts, key=zone_counts.get)
            insights.append({
                "type" : "info",
                "text": f"Highest activity zone: '{top_zone}' ({zone_counts[top_zone]} detections)."
            })
            
        #Low confidence warning 
        low_con = [d for d in all_detections if d.confidence <0.3]
        if len(low_con) / total * 0.3:
            insights.append({
                "type": "warning",
                "text": f"{len(low_con)} detections ({round(len(low_con)/total*100,2)}%) have confidence below 30%. Consider raising the detection threshold."
            })
        
        # Response
        return{
            "total" : total,
            "filters_applied" : {
                "date_from" : date_from,
                "date_to" : date_to,
                "class_names" : class_names,
                "camera_ids" : camera_ids
            },
            "detection_counts" : detection_counts,
            "activity_intensity" : activity_intensity,
            "peak_hours" : peak_hours,
            "zone_analytics" : zone_analytics,
            "object_analytics" : object_analytics,
            "alert_analytics" : alert_analytics,
            "camera_analytics" : camera_analytics,
            "trend_analytics" : trend_analytics,
            "average_detection_rate_per_hour" : avg_rate,
            "no_activity_periods" : no_activity_periods[:10], # top 10 longest gaps
            "timeline_chart" : timeline_chart,
            "smart_insights" : insights
        }
    
            
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)