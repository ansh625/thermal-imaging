from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import os
import uuid
import cv2
import asyncio
import base64
from pathlib import Path

from database import get_db, init_db, User, Camera
from auth import (authenticate_user, create_access_token, get_current_active_user,
                  get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES)
from camera_handler import camera_manager

app = FastAPI(title="ThermalStream API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path("uploads").mkdir(exist_ok=True)
Path("recordings").mkdir(exist_ok=True)

@app.on_event("startup")
async def startup():
    init_db()
    print("✅ Server started successfully")

@app.post("/api/auth/signup")
async def signup(email: str, password: str, full_name: str, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(email=email, hashed_password=get_password_hash(password),
                full_name=full_name, role="operator")
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created", "user": {"id": user.id, "email": user.email}}

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name}
    }

@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name}

@app.post("/api/camera/connect")
async def connect_camera(url: str, camera_id: int = 1,
                         current_user: User = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    urls_to_try = camera_manager.parse_camera_url(url)
    session_id = str(uuid.uuid4())
    session = None
    
    for attempt_url in urls_to_try:
        session = await camera_manager.create_session(session_id, attempt_url, camera_id)
        if session:
            break
    
    if not session:
        raise HTTPException(status_code=400, detail="Failed to connect")
    
    camera = Camera(name=f"Camera {camera_id}", connection_url=url,
                    status="connected", user_id=current_user.id)
    db.add(camera)
    db.commit()
    
    return {"session_id": session_id, "camera_id": camera_id, "fps": session.fps}

@app.post("/api/camera/disconnect")
async def disconnect_camera(session_id: str, current_user: User = Depends(get_current_active_user)):
    await camera_manager.disconnect_session(session_id)
    return {"message": "Disconnected"}

@app.websocket("/ws/video/{session_id}")
async def video_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        camera_session = camera_manager.get_session(session_id)
        if not camera_session:
            await websocket.close()
            return
        
        while camera_session.is_running:
            frame = await camera_session.get_frame()
            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                await websocket.send_json({"frame": frame_b64})
            await asyncio.sleep(1.0 / camera_session.fps)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")

@app.get("/")
async def root():
    return {"app": "ThermalStream API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)