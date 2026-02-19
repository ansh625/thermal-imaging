from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Optional, List, Dict
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        ],
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

# ==================== CAMERA MANAGEMENT ====================

@app.post("/api/camera/connect")
async def connect_camera(url: str, camera_id: int = 1,
                        current_user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    """Connect to camera"""
    urls_to_try = camera_manager.parse_camera_url(url)
    session_id = str(uuid.uuid4())
    session = None
    
    for attempt_url in urls_to_try:
        session = await camera_manager.create_session(session_id, attempt_url, camera_id)
        if session:
            break
    
    if not session:
        raise HTTPException(status_code=400, detail="Failed to connect to camera")
    
    # Update or create camera in database
    camera = db.query(Camera).filter(
        Camera.user_id == current_user.id,
        Camera.connection_url == url
    ).first()
    
    if not camera:
        camera = Camera(
            name=f"Camera {camera_id}",
            connection_type="rtsp" if "rtsp" in str(url) else "usb" if str(url).isdigit() else "http",
            connection_url=url,
            user_id=current_user.id
        )
        db.add(camera)
    
    camera.status = "connected"
    camera.session_id = session_id
    camera.fps = session.fps
    camera.last_seen = datetime.utcnow()
    camera.resolution = "1280x720"
    db.commit()
    db.refresh(camera)
    
    # Check if there's an active schedule and auto-start recording
    active_schedule = scheduler_service.get_active_schedule_for_camera(camera.id)
    auto_recording_started = False
    
    if active_schedule:
        try:
            # Auto-start recording for scheduled recording
            filepath = recording_manager.start_recording(
                session_id,
                session.fps,
                (1280, 720),
                camera.name
            )
            
            if filepath:
                # Create database entry
                recording = Recording(
                    filename=os.path.basename(filepath),
                    format="mp4",
                    storage_path=filepath,
                    camera_id=camera.id,
                    user_id=current_user.id,
                    started_at=datetime.utcnow(),
                    is_scheduled=True
                )
                db.add(recording)
                db.commit()
                
                auto_recording_started = True
                logger.info(f"Auto-started recording for camera {camera.id} (schedule: {active_schedule.name})")
                
                # Notification
                notification_service.create_notification(
                    user_id=current_user.id,
                    title="Scheduled Recording Started",
                    message=f"Auto recording started for {camera.name} ({active_schedule.name})",
                    type="info",
                    data={"recording_id": recording.id, "camera_id": camera.id, "schedule_id": active_schedule.id}
                )
        except Exception as e:
            logger.error(f"Error auto-starting scheduled recording: {e}")
    
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
            "fps": session.fps,
            "auto_recording": auto_recording_started
        }
    )
    
    return {
        "session_id": session_id,
        "camera_id": camera.id,
        "fps": session.fps,
        "resolution": "1280x720",
        "status": "connected",
        "auto_recording": auto_recording_started,
        "active_schedule": {
            "id": active_schedule.id,
            "name": active_schedule.name
        } if active_schedule else None
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
async def video_stream(websocket: WebSocket, session_id: str):
    """WebSocket video streaming with optimized detection"""
    await websocket.accept()
    
    detection_enabled = False
    detection_confidence = 0.5
    db = next(get_db())
    frame_count = 0
    scheduled_recording_active = False
    
    # Detection frequency: run detection every N frames
    # Lower = more frequent detection, higher CPU
    # Higher = smoother video, less frequent detection
    DETECTION_INTERVAL = 2  # Run detection every 2 frames (better balance)
    
    try:
        camera_session = camera_manager.get_session(session_id)
        if not camera_session:
            await websocket.close()
            return
        
        # Get camera from database
        camera = db.query(Camera).filter(Camera.session_id == session_id).first()
        if not camera:
            await websocket.close()
            return
        
        while camera_session.is_running:
            # Check for client messages (detection control)
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=0.001)
                if message.get('type') == 'toggle_detection':
                    detection_enabled = message.get('enabled', False)
                    detection_confidence = message.get('confidence', 0.5)
                    if not detection_enabled:
                        detection_cache.clear(session_id)
            except asyncio.TimeoutError:
                pass
            
            # Check if scheduled recording should be active (every 30 frames ~1 second)
            if frame_count % 30 == 0:
                try:
                    should_record = scheduler_service.is_scheduled_recording_active(camera.id)
                    
                    # Start recording if scheduled and not already recording
                    if should_record and not recording_manager.is_recording(session_id) and not scheduled_recording_active:
                        logger.info(f"Starting scheduled recording for camera {camera.id} (session: {session_id})")
                        filepath = recording_manager.start_recording(
                            session_id,
                            camera_session.fps,
                            (1280, 720),
                            camera.name
                        )
                        
                        if filepath:
                            recording = Recording(
                                filename=os.path.basename(filepath),
                                format="mp4",
                                storage_path=filepath,
                                camera_id=camera.id,
                                user_id=camera.user_id,
                                started_at=datetime.utcnow(),
                                is_scheduled=True
                            )
                            db.add(recording)
                            db.commit()
                            scheduled_recording_active = True
                            logger.info(f"Scheduled recording started for camera {camera.id}")
                    
                    # Stop recording if schedule is no longer active
                    elif not should_record and (recording_manager.is_recording(session_id) or scheduled_recording_active):
                        logger.info(f"Stopping scheduled recording for camera {camera.id}")
                        recording_manager.stop_recording(session_id)
                        scheduled_recording_active = False
                        
                except Exception as e:
                    logger.error(f"Error checking scheduled recording: {e}")
            
            frame = await camera_session.get_frame()
            if frame is None:
                await asyncio.sleep(0.005)
                continue
            
            frame_count += 1
            original_frame = frame.copy()
            display_frame = frame.copy()
            
            # YOLO Detection - run every N frames
            # This keeps CPU usage reasonable while maintaining smooth video
            if detection_enabled and frame_count % DETECTION_INTERVAL == 0:
                try:
                    detections = yolo_detector.detect(display_frame, detection_confidence)
                    if detections:
                        # Cache the detections so they persist across frames
                        detection_cache.update(session_id, detections)
                        
                        # Save to database (non-blocking via asyncio)
                        loop = asyncio.get_event_loop()
                        loop.run_in_executor(
                            None,
                            lambda: _save_detections_sync(db, camera.id, detections, original_frame)
                        )
                except Exception as e:
                    logger.error(f"Detection error: {e}")
            
            # Get cached detections (persist even if detection isn't running this frame)
            # This eliminates blinking!
            current_detections = detection_cache.get(session_id) if detection_enabled else []
            
            # Draw cached detections on EVERY frame
            if current_detections and detection_enabled:
                display_frame = yolo_detector.draw_detections(display_frame, current_detections)
            
            # Recording - record with detection boxes if detections exist
            if recording_manager.is_recording(session_id):
                # Create a copy for recording with detections drawn
                recording_frame = original_frame.copy()
                if current_detections and detection_enabled:
                    recording_frame = yolo_detector.draw_detections(recording_frame, current_detections)
                recording_manager.write_frame(session_id, recording_frame)
            
            # Encode with optimized quality
            _, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            try:
                await asyncio.wait_for(
                    websocket.send_json({
                        "frame": frame_b64,
                        "detections": current_detections,
                        "recording": recording_manager.is_recording(session_id),
                        "frame_count": frame_count
                    }),
                    timeout=0.05
                )
            except asyncio.TimeoutError:
                logger.debug(f"WebSocket send timeout for {session_id}")
                continue
            
            # Keep stream smooth - minimal sleep
            await asyncio.sleep(0.005)  # ~200 FPS max upstream
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        detection_cache.clear(session_id)
        db.close()


def _save_detections_sync(db: Session, camera_id: int, detections: List[Dict], frame: np.ndarray):
    """Save detections to database (sync, runs in thread pool)"""
    try:
        for det in detections:
            try:
                screenshot_path = yolo_detector.save_detection(frame, det)
                detection_record = Detection(
                    camera_id=camera_id,
                    class_name=det['class_name'],
                    confidence=det['confidence'],
                    bbox_x1=det['bbox']['x1'],
                    bbox_y1=det['bbox']['y1'],
                    bbox_x2=det['bbox']['x2'],
                    bbox_y2=det['bbox']['y2'],
                    screenshot_path=screenshot_path,
                    detected_at=datetime.utcnow()
                )
                db.add(detection_record)
            except Exception as e:
                logger.error(f"Error saving detection: {e}")
        db.commit()
    except Exception as e:
        logger.error(f"Error committing detections: {e}")
        db.rollback()

# ==================== RECORDING MANAGEMENT ====================

@app.post("/api/recording/start")
async def start_recording(session_id: str,
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
        started_at=datetime.utcnow()
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    
    # Notification
    notification_service.create_notification(
        user_id=current_user.id,
        title="Recording Started",
        message=f"Recording started for {camera.name}",
        type="info",
        data={"recording_id": recording.id, "camera_id": camera.id}
    )
    
    # Broadcast
    await websocket_manager.broadcast_to_user(
        current_user.id,
        "recording_started",
        {"recording_id": recording.id, "camera_id": camera.id}
    )
    
    return {
        "recording_id": recording.id,
        "filename": recording.filename,
        "started_at": recording.started_at
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
    
    return FileResponse(
        recording.storage_path,
        filename=recording.filename,
        media_type='video/mp4'
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
        
        cv2.imwrite(filepath, frame)
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)