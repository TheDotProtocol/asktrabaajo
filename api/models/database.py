from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./asktrabaajo.db")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # jobseeker, employer, consultant, government, foreign_company
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)
    tests = relationship("TestResult", back_populates="user")
    jobs_posted = relationship("Job", back_populates="employer")
    applications = relationship("Application", back_populates="jobseeker")

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Personal Information
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String)
    location = Column(String)
    citizenship = Column(String)
    
    # Skills (JSON format for flexibility)
    technical_skills = Column(JSON, default=list)
    soft_skills = Column(JSON, default=list)
    languages = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    
    # Work Experience (JSON format)
    work_experience = Column(JSON, default=list)
    education = Column(JSON, default=list)
    
    # Preferences
    salary_expectation = Column(Float)
    availability = Column(String)
    remote_preference = Column(Boolean, default=False)
    
    # Government specific fields
    government_id = Column(String)
    agency_name = Column(String)
    agency_document = Column(String)  # File path
    
    # Business specific fields (for employers/consultants)
    company_name = Column(String)
    business_license = Column(String)
    company_size = Column(String)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")

class TestResult(Base):
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    test_type = Column(String, nullable=False)  # general, technical, personality
    score = Column(Integer, nullable=False)  # 0-20
    max_score = Column(Integer, default=20)
    answers = Column(JSON, default=dict)
    duration_minutes = Column(Integer)
    completed_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tests")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSON, default=list)
    min_score_required = Column(Integer, default=0)
    salary_range_min = Column(Float)
    salary_range_max = Column(Float)
    location = Column(String)
    is_remote = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    employer = relationship("User", back_populates="jobs_posted")
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    jobseeker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default="applied")  # applied, shortlisted, interviewed, offered, rejected
    applied_at = Column(DateTime, default=func.now())
    
    # Relationships
    jobseeker = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    interviews = relationship("Interview", back_populates="application")

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(String, default="scheduled")  # scheduled, in_progress, completed, cancelled
    room_id = Column(String, unique=True)
    recording_url = Column(String)
    analysis_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    application = relationship("Application", back_populates="interviews")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_method = Column(String, nullable=False)  # stripe, crypto
    crypto_type = Column(String)  # 3DOT, ASK, ARHC, USDT, BTC, BNB
    transaction_id = Column(String, unique=True)
    status = Column(String, default="pending")  # pending, completed, failed, refunded
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=func.now())

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine) 