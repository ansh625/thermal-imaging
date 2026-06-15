"""
database.py  ── MODIFIED for Smart Recording
═════════════════════════════════════════════════════════════════════════════
Changes from original:
  1. Recording table gets two new nullable columns:
       • is_smart_clip  (Boolean) – True when created by SmartRecordingManager
       • event_classes  (JSON)    – List of YOLO class names in the clip
 
  2. New SmartClipEvent table for fine-grained event metadata (optional;
     useful for the analytics dashboard and future search features).
 
  Everything else is IDENTICAL to the original database.py.
 
HOW TO APPLY
────────────────
  a) Replace your existing database.py with this file.
  b) The new columns use nullable=True with safe defaults, so existing
     SQLite databases are upgraded automatically on next startup via
     init_db() → Base.metadata.create_all().
     For production PostgreSQL you would run Alembic migrations instead.
═════════════════════════════════════════════════════════════════════════════
"""
 
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Float, JSON, ForeignKey, Text
)
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
 
 
# ──────────────────────────────────────────────────────────────────────────────
# EXISTING MODELS  (unchanged except Recording – see ★ markers)
# ──────────────────────────────────────────────────────────────────────────────
 
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="operator")
    is_active = Column(Boolean, default=True)
    organization = Column(String)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
 
    cameras = relationship("Camera", back_populates="owner",
                           cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="user",
                              cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user",
                                 cascade="all, delete-orphan")
 
 
class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    connection_type = Column(String)        # usb, rtsp, http
    connection_url = Column(String)
    status = Column(String, default="disconnected")
    last_seen = Column(DateTime)
    fps = Column(Float, default=0)
    resolution = Column(String)
    session_id = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
 
    owner = relationship("User", back_populates="cameras")
    recordings = relationship("Recording", back_populates="camera",
                              cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="camera",
                              cascade="all, delete-orphan")
    schedules = relationship("RecordingSchedule", back_populates="camera",
                             cascade="all, delete-orphan")
    # ★ NEW: link to smart clip events for this camera
    smart_clip_events = relationship("SmartClipEvent", back_populates="camera",
                                     cascade="all, delete-orphan")
 
 
class Recording(Base):
    """
    Stores both traditional continuous recordings and smart event clips.
 
    ★ NEW columns
    ─────────────
    is_smart_clip : True when this row was created by SmartRecordingManager.
                    False (default) for all legacy recordings → zero migration pain.
 
    event_classes : JSON list of YOLO class names detected in the clip,
                    e.g. ["person", "car"].  NULL for non-smart recordings.
    """
    __tablename__ = "recordings"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    format = Column(String)
    duration_seconds = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    storage_path = Column(String)
    thumbnail_path = Column(String)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    is_scheduled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
 
    # ★ NEW – smart recording metadata
    is_smart_clip = Column(Boolean, default=False, nullable=True)
    event_classes = Column(JSON, nullable=True)  # e.g. ["person", "car"]
 
    camera = relationship("Camera", back_populates="recordings")
    user = relationship("User", back_populates="recordings")
 
 
class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String)
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
    name = Column(String)
    days_of_week = Column(JSON)         # ["Monday", "Tuesday", ...]
    start_time = Column(String)         # "09:00"
    end_time = Column(String)           # "17:00"
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    camera = relationship("Camera", back_populates="schedules")
 
 
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    type = Column(String)               # info, success, warning, error
    is_read = Column(Boolean, default=False)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="notifications")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# ★ NEW MODEL: SmartClipEvent
# ──────────────────────────────────────────────────────────────────────────────
 
class SmartClipEvent(Base):
    """
    Fine-grained event record linked to a smart clip.
 
    One SmartClipEvent row is created per saved clip (by SmartRecordingManager).
    Stores richer metadata than the Recording row so the analytics dashboard
    can answer questions like:
      • "How many person events per camera this week?"
      • "Average event duration?"
      • "Storage saved vs continuous recording?"
 
    Relationship:
        SmartClipEvent  →  Recording  (recording_id FK)
        SmartClipEvent  →  Camera     (camera_id FK)
 
    NOTE: This table is entirely additive.  The rest of the application
    continues to work with just the Recording table.
    """
    __tablename__ = "smart_clip_events"
 
    id = Column(Integer, primary_key=True, index=True)
 
    # ── FK links ───────────────────────────────────────────────────────────
    recording_id = Column(Integer, ForeignKey("recordings.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
 
    # ── Event window ───────────────────────────────────────────────────────
    event_start = Column(DateTime, nullable=False)   # first detection timestamp
    event_end = Column(DateTime, nullable=False)     # last detection timestamp
    clip_start = Column(DateTime, nullable=False)    # includes pre-event buffer
    clip_end = Column(DateTime, nullable=False)      # includes post-event tail
 
    # ── Detection summary ──────────────────────────────────────────────────
    total_detections = Column(Integer, default=0)
    detected_classes = Column(JSON, nullable=True)   # ["person", "car"]
    primary_class = Column(String, nullable=True)    # most frequent class
 
    # ── Clip file info ─────────────────────────────────────────────────────
    clip_filename = Column(String, nullable=True)
    clip_path = Column(String, nullable=True)
    clip_duration_seconds = Column(Float, default=0)
    clip_size_bytes = Column(Integer, default=0)
    frame_count = Column(Integer, default=0)
 
    # ── Storage savings estimate ───────────────────────────────────────────
    # How many seconds of continuous recording were skipped by using smart mode
    idle_seconds_skipped = Column(Float, default=0, nullable=True)
 
    created_at = Column(DateTime, default=datetime.utcnow)
 
    # ── Relationships ──────────────────────────────────────────────────────
    camera = relationship("Camera", back_populates="smart_clip_events")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# DB UTILITIES  (unchanged)
# ──────────────────────────────────────────────────────────────────────────────
 
def init_db():
    """
    Create all tables.  Safe to call multiple times.
    New columns on existing tables are handled by SQLAlchemy's create_all
    for SQLite (it adds missing tables but does NOT add columns to existing
    ones).  For new column additions on a live SQLite DB, use Alembic or
    run the one-liner migration helper below.
    """
    Base.metadata.create_all(bind=engine)
    _sqlite_add_missing_columns()
 
 
def _sqlite_add_missing_columns():
    """
    SQLite-specific migration helper.
    Adds new columns to existing tables if they don't exist yet.
    Safe to call on every startup; no-ops if columns already exist.
    """
    if "sqlite" not in DATABASE_URL:
        return  # For PostgreSQL/MySQL use Alembic migrations
 
    new_columns = [
        # (table_name, column_name, column_definition)
        ("recordings", "is_smart_clip", "BOOLEAN DEFAULT 0"),
        ("recordings", "event_classes", "JSON"),
    ]
 
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
 
    with engine.connect() as conn:
        for table, col, col_def in new_columns:
            if table not in existing_tables:
                continue
            existing_cols = [c["name"] for c in inspector.get_columns(table)]
            if col not in existing_cols:
                try:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                    )
                    conn.commit()
                    print(f"✅ Migration: added {table}.{col}")
                except Exception as e:
                    print(f"⚠️  Migration warning ({table}.{col}): {e}")
 
 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()