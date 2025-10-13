from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/asktrabaajo")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)

# Simplified Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)  # jobseeker, employer, consultant, government, foreign
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic Profile Info
    phone = Column(String(20))
    location = Column(String(100))
    bio = Column(Text)
    
    # Skills and Experience (JSON format for flexibility)
    skills = Column(JSON)
    experience = Column(JSON)
    education = Column(JSON)
    certifications = Column(JSON)
    
    # Government & Foreign Company Specific
    security_clearance_level = Column(String(50))
    visa_status = Column(String(50))
    international_eligibility = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Simple relationship
    user = relationship("User")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Job Details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSON)  # Skills, experience, etc.
    salary_range = Column(JSON)  # {min: 50000, max: 80000, currency: "USD"}
    
    # Job Status
    status = Column(String(20), default="active")  # active, closed, draft
    
    # Government & Foreign Company Specific
    security_clearance_required = Column(Boolean, default=False)
    international_candidates = Column(Boolean, default=False)
    visa_sponsorship = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Simple relationship
    employer = relationship("User")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Application Status
    status = Column(String, default="pending")  # pending, reviewed, shortlisted, rejected, hired
    
    # Matching Score
    match_score = Column(Float)  # AI-calculated match percentage
    test_score = Column(Float)  # Applicant's test score
    
    # Application Details
    cover_letter = Column(Text)
    expected_salary = Column(Float)
    
    applied_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Simple relationships
    job = relationship("Job")
    applicant = relationship("User")

class TestResult(Base):
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Test Details
    test_type = Column(String(50), nullable=False)  # technical, behavioral, skills
    questions = Column(JSON)  # List of questions asked
    answers = Column(JSON)  # User's answers
    score = Column(Float, nullable=False)
    max_score = Column(Float, default=100.0)
    
    # AI Analysis
    ai_analysis = Column(JSON)  # AI insights and recommendations
    
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    # Simple relationship
    user = relationship("User")

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Interview Details
    room_id = Column(String, unique=True, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    
    # Interview Status
    status = Column(String, default="scheduled")  # scheduled, in_progress, completed, cancelled
    
    # Video Call Details
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    recording_url = Column(String)
    
    # Analysis Results
    facial_analysis = Column(JSON)  # Facial expression analysis
    technical_issues = Column(JSON)
    
    # Cost and Billing
    cost_per_minute = Column(Float, default=1.0)
    total_cost = Column(Float)
    payment_status = Column(String, default="pending")  # pending, paid, refunded
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Simple relationships
    application = relationship("Application")
    participant = relationship("User")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    
    # Payment Details
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_method = Column(String, nullable=False)  # stripe, crypto, bank_transfer
    
    # Payment Status
    status = Column(String, default="pending")  # pending, completed, failed, refunded
    
    # Transaction Details
    transaction_id = Column(String)
    stripe_payment_intent_id = Column(String)
    crypto_transaction_hash = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Simple relationships
    user = relationship("User")
    interview = relationship("Interview")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Notification Details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)  # job_match, interview_scheduled, payment_received, etc.
    
    # Status
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    
    # Additional Data
    extra_data = Column(JSON)  # Additional data for the notification
    
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    
    # Simple relationship
    user = relationship("User")
