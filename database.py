import os
import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import IntegrityError

# Fallback to local SQLite if DATABASE_URL (Supabase/Railway) is missing
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///rsvp_app.db')

# Railway/Heroku sometimes provide 'postgres://' — SQLAlchemy requires 'postgresql://'
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# SQLAlchemy setup
kwargs = {'pool_pre_ping': True}  # Verify connections before use
if DATABASE_URL.startswith('sqlite'):
    kwargs['connect_args'] = {'check_same_thread': False}

engine = create_engine(DATABASE_URL, **kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_premium = Column(Boolean, default=False)
    
    # Relationships
    readings = relationship("Reading", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("ReadingSession", back_populates="user", cascade="all, delete-orphan")

class Reading(Base):
    __tablename__ = 'readings'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String)
    text_content = Column(Text)
    saved_index = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="readings")

class UserSettings(Base):
    __tablename__ = 'user_settings'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    wpm = Column(Integer, default=300)
    theme = Column(String, default='dark')
    font_family = Column(String, default='Inter')
    bg_color = Column(String, default='')
    text_color = Column(String, default='')
    
    user = relationship("User", back_populates="settings")

class ReadingSession(Base):
    __tablename__ = 'reading_sessions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    words_read = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("[DB] Tables created/verified successfully.")
    except Exception as e:
        print(f"[DB] WARNING: Could not connect to database on startup: {e}")
        print("[DB] App will start, but DB operations may fail. Check DATABASE_URL env var.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper hash func
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- Auth ---
def create_user(email: str, username: str, password: str) -> bool:
    db = SessionLocal()
    try:
        new_user = User(
            email=email,
            username=username,
            password_hash=hash_password(password)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Initialize default settings
        new_settings = UserSettings(user_id=new_user.id)
        db.add(new_settings)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    finally:
        db.close()

def login(email: str, password: str) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email, User.password_hash == hash_password(password)).first()
        if user:
            return True, {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_premium": user.is_premium
            }
        return False, "Invalid credentials"
    finally:
        db.close()

# --- Readings ---
def save_reading(user_id: int, reading_id: int, text: str, index: int, title: str) -> int:
    if not user_id: return None
    db = SessionLocal()
    try:
        if reading_id:
            reading = db.query(Reading).filter(Reading.id == reading_id, Reading.user_id == user_id).first()
            if reading:
                reading.text_content = text
                reading.saved_index = index
                reading.last_accessed = datetime.utcnow()
                db.commit()
                return reading.id
        
        # New Reading
        new_reading = Reading(
            user_id=user_id,
            title=title,
            text_content=text,
            saved_index=index,
            last_accessed=datetime.utcnow()
        )
        db.add(new_reading)
        db.commit()
        db.refresh(new_reading)
        return new_reading.id
    finally:
        db.close()

def get_readings(user_id: int):
    if not user_id: return []
    db = SessionLocal()
    try:
        readings = db.query(Reading).filter(Reading.user_id == user_id).order_by(Reading.last_accessed.desc()).all()
        return [{"id": r.id, "title": r.title, "index": r.saved_index, "date": r.last_accessed.isoformat()} for r in readings]
    finally:
        db.close()

def get_reading_content(reading_id: int, user_id: int) -> tuple[str, int]:
    db = SessionLocal()
    try:
        reading = db.query(Reading).filter(Reading.id == reading_id, Reading.user_id == user_id).first()
        if reading:
            reading.last_accessed = datetime.utcnow()
            db.commit()
            return reading.text_content, reading.saved_index
        return "", 0
    finally:
        db.close()

def delete_reading(reading_id: int, user_id: int):
    db = SessionLocal()
    try:
        reading = db.query(Reading).filter(Reading.id == reading_id, Reading.user_id == user_id).first()
        if reading:
            db.delete(reading)
            db.commit()
    finally:
        db.close()

# --- Settings & Analytics ---
def save_user_settings(user_id: int, settings_data: dict) -> bool:
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            
        if 'wpm' in settings_data: settings.wpm = settings_data['wpm']
        if 'theme' in settings_data: settings.theme = settings_data['theme']
        if 'font_family' in settings_data: settings.font_family = settings_data['font_family']
        if 'bg_color' in settings_data: settings.bg_color = settings_data['bg_color']
        if 'text_color' in settings_data: settings.text_color = settings_data['text_color']
        
        db.commit()
        return True
    finally:
        db.close()

def get_user_settings(user_id: int) -> dict:
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings:
            return {
                "wpm": settings.wpm,
                "theme": settings.theme,
                "font_family": settings.font_family,
                "bg_color": settings.bg_color,
                "text_color": settings.text_color
            }
        return {} # Defaults handled by frontend
    finally:
        db.close()

def log_reading_session(user_id: int, words_read: int, duration_seconds: int):
    if not user_id or words_read == 0: return
    db = SessionLocal()
    try:
        session = ReadingSession(
            user_id=user_id,
            words_read=words_read,
            duration_seconds=duration_seconds,
            created_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
    finally:
        db.close()
