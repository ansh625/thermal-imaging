from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, JSON, ForeignKey
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
    created_at = Column(DateTime, default=datetime.utcnow)
    cameras = relationship("Camera", back_populates="owner")
    recordings = relationship("Recording", back_populates="user")

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    connection_type = Column(String)
    connection_url = Column(String)
    status = Column(String, default="disconnected")
    last_seen = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="cameras")
    recordings = relationship("Recording", back_populates="camera")

class Recording(Base):
    __tablename__ = "recordings"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    format = Column(String)
    duration_seconds = Column(Integer)
    file_size_bytes = Column(Integer)
    storage_path = Column(String)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    camera = relationship("Camera", back_populates="recordings")
    user = relationship("User", back_populates="recordings")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()