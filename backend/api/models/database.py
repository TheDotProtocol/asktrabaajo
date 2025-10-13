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

# Database Models
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
    
    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)
    jobs_posted = relationship("Job", back_populates="employer")
    applications = relationship("Application", back_populates="applicant")
    test_results = relationship("TestResult", back_populates="user")
    interviews = relationship("Interview", back_populates="participant")
    payments = relationship("Payment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    documents = relationship("Document", foreign_keys="Document.user_id")
    compliance_logs = relationship("ComplianceLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic Information
    phone = Column(String)
    date_of_birth = Column(DateTime)
    location = Column(String)
    bio = Column(Text)
    
    # Skills and Experience
    skills = Column(JSON)  # List of skills with proficiency levels
    experience = Column(JSON)  # Work experience details
    education = Column(JSON)  # Educational background
    certifications = Column(JSON)  # Professional certifications
    
    # Job Seeker Specific
    desired_salary = Column(Float)
    preferred_locations = Column(JSON)
    remote_preference = Column(Boolean, default=False)
    
    # Employer Specific
    company_name = Column(String)
    company_size = Column(String)
    industry = Column(String)
    website = Column(String)
    
    # Government Specific
    government_id = Column(String)
    department = Column(String)
    official_documents = Column(JSON)  # Document URLs
    security_clearance_level = Column(String)  # Basic, Secret, Top Secret
    clearance_expiry_date = Column(DateTime)
    government_contracts = Column(JSON)  # Active government contracts
    compliance_status = Column(String, default="pending")  # pending, verified, rejected
    
    # Foreign Company Specific
    country = Column(String)
    business_license = Column(String)
    tax_id = Column(String)
    registration_number = Column(String)
    legal_entity_type = Column(String)  # LLC, Corporation, Partnership, etc.
    foreign_currency_preference = Column(String, default="USD")
    international_compliance = Column(JSON)  # Compliance with international laws
    visa_sponsorship_capability = Column(Boolean, default=False)
    
    # Enhanced Security & Verification
    identity_verified = Column(Boolean, default=False)
    background_check_status = Column(String, default="pending")
    document_verification_status = Column(String, default="pending")
    facial_verification_status = Column(String, default="pending")
    blockchain_verification_hash = Column(String)  # For immutable verification
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="profile")

class TestResult(Base):
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Test Details
    test_type = Column(String, nullable=False)  # general, technical, role_specific
    questions = Column(JSON, nullable=False)  # Question details
    answers = Column(JSON, nullable=False)  # User answers
    score = Column(Float, nullable=False)  # Score out of 20
    max_score = Column(Float, default=20.0)
    
    # Scoring Breakdown
    skills_score = Column(Float)  # Skills/experience component
    test_score = Column(Float)  # Test performance component
    negative_score = Column(Float, default=0.0)  # Penalties for mismatches
    
    # AI Analysis
    ai_insights = Column(JSON)  # AI-generated insights and feedback
    
    # Metadata
    duration_minutes = Column(Integer)
    completed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="test_results")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Job Details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSON)  # Required skills and qualifications
    min_score = Column(Float)  # Minimum test score required
    salary_range = Column(JSON)  # Min and max salary
    location = Column(String)
    remote_allowed = Column(Boolean, default=False)
    
    # Job Status
    status = Column(String, default="active")  # active, paused, closed, filled
    job_type = Column(String)  # full_time, part_time, contract, internship
    
    # Application Details
    application_deadline = Column(DateTime)
    max_applications = Column(Integer)
    
    # Government & Foreign Company Specific
    security_clearance_required = Column(String)  # None, Basic, Secret, Top Secret
    government_contract_related = Column(Boolean, default=False)
    contract_number = Column(String)  # Government contract number
    compliance_requirements = Column(JSON)  # Specific compliance needs
    visa_sponsorship_available = Column(Boolean, default=False)
    international_relocation = Column(Boolean, default=False)
    currency = Column(String, default="USD")  # Multi-currency support
    tax_implications = Column(JSON)  # Tax information for foreign workers
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employer = relationship("User", back_populates="jobs_posted")
    applications = relationship("Application", back_populates="job")

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
    
    # AI Analysis
    ai_analysis = Column(JSON)  # AI-powered matching analysis
    
    # Application Details
    cover_letter = Column(Text)
    expected_salary = Column(Float)
    
    # Government & Foreign Company Specific
    security_clearance_match = Column(Boolean, default=False)
    compliance_verification_status = Column(String, default="pending")
    document_submission_status = Column(String, default="pending")
    visa_requirements_met = Column(Boolean, default=False)
    international_eligibility = Column(Boolean, default=False)
    
    # Timestamps
    applied_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    applicant = relationship("User", back_populates="applications")
    interviews = relationship("Interview", back_populates="application")

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
    background_noise = Column(Boolean, default=False)
    technical_issues = Column(JSON)
    
    # Cost and Billing
    cost_per_minute = Column(Float, default=1.0)
    total_cost = Column(Float)
    payment_status = Column(String, default="pending")  # pending, paid, refunded
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    application = relationship("Application", back_populates="interviews")
    participant = relationship("User", back_populates="interviews")
    payments = relationship("Payment", back_populates="interview")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    
    # Payment Details
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_method = Column(String, nullable=False)  # stripe, crypto_3dot, crypto_ask, crypto_arhc, crypto_usdt, crypto_btc, crypto_bnb
    
    # Crypto Details
    crypto_wallet_address = Column(String)
    crypto_transaction_hash = Column(String)
    crypto_amount = Column(Float)
    
    # Stripe Details
    stripe_payment_intent_id = Column(String)
    stripe_charge_id = Column(String)
    
    # Payment Status
    status = Column(String, default="pending")  # pending, processing, completed, failed, refunded
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    refunded_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    interview = relationship("Interview", back_populates="payments")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Log Details
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)  # login, register, profile_update, test_taken, job_posted, etc.
    resource_type = Column(String)  # user, profile, job, application, etc.
    resource_id = Column(Integer)
    
    # Request Details
    ip_address = Column(String)
    user_agent = Column(String)
    request_data = Column(JSON)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User") 

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Document Details
    document_type = Column(String, nullable=False)  # passport, license, certificate, contract, etc.
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String)
    
    # Verification Status
    verification_status = Column(String, default="pending")  # pending, verified, rejected
    verified_by = Column(Integer, ForeignKey("users.id"))
    verified_at = Column(DateTime)
    verification_notes = Column(Text)
    
    # Security & Compliance
    encryption_hash = Column(String)  # Document integrity verification
    blockchain_hash = Column(String)  # Immutable verification
    access_level = Column(String, default="private")  # private, shared, public
    
    # Metadata
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Document expiry date
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    verifier = relationship("User", foreign_keys=[verified_by])

class ComplianceLog(Base):
    __tablename__ = "compliance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Compliance Details
    compliance_type = Column(String, nullable=False)  # gdpr, pdpa, security_clearance, etc.
    status = Column(String, default="pending")  # pending, compliant, non_compliant
    requirements = Column(JSON)  # Specific compliance requirements
    verification_data = Column(JSON)  # Verification results
    
    # Audit Information
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # Compliance expiry date
    
    # Relationships
    user = relationship("User")

class Currency(Base):
    __tablename__ = "currencies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Currency Details
    code = Column(String, unique=True, nullable=False)  # USD, EUR, THB, etc.
    name = Column(String, nullable=False)
    symbol = Column(String)
    exchange_rate_usd = Column(Float, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_crypto = Column(Boolean, default=False)
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # email, realtime, system
    status = Column(String(20), default="unread")  # unread, read, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="notifications") 