from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./thermalstream.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="operator")
    is_active = Column(Boolean, default=True)
    organization = Column(String)
    reset_token = Column(String, nullable=True)  # For password reset
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    cameras = relationship("Camera", back_populates="owner", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    connection_type = Column(String)  # usb, rtsp, http
    connection_url = Column(String)
    status = Column(String, default="disconnected")  # connected, disconnected, error
    last_seen = Column(DateTime)
    fps = Column(Float, default=0)
    resolution = Column(String)
    session_id = Column(String)  # Current active session
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="cameras")
    recordings = relationship("Recording", back_populates="camera", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="camera", cascade="all, delete-orphan")
    schedules = relationship("RecordingSchedule", back_populates="camera", cascade="all, delete-orphan")

class Recording(Base):
    __tablename__ = "recordings"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    format = Column(String)  # mp4, avi
    duration_seconds = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    storage_path = Column(String)
    thumbnail_path = Column(String)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    is_scheduled = Column(Boolean, default=False)  # Whether it's from scheduler
    created_at = Column(DateTime, default=datetime.utcnow)
    camera = relationship("Camera", back_populates="recordings")
    user = relationship("User", back_populates="recordings")

class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String)  # person, car, etc.
    confidence = Column(Float)
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)
    screenshot_path = Column(String)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    recording_id = Column(Integer, ForeignKey("recordings.id"), nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    camera = relationship("Camera", back_populates="detections")

class RecordingSchedule(Base):
    __tablename__ = "recording_schedules"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    name = Column(String)  # Schedule name
    days_of_week = Column(JSON)  # ["Monday", "Tuesday", ...]
    start_time = Column(String)  # "09:00"
    end_time = Column(String)  # "17:00"
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    camera = relationship("Camera", back_populates="schedules")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    type = Column(String)  # info, success, warning, error
    is_read = Column(Boolean, default=False)
    data = Column(JSON, nullable=True)  # Additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="notifications")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()