from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Profile Schemas
class ProfileBase(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[Dict[str, Any]] = None
    experience: Optional[Dict[str, Any]] = None
    education: Optional[Dict[str, Any]] = None
    certifications: Optional[Dict[str, Any]] = None

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Job Schemas
class JobBase(BaseModel):
    title: str
    description: str
    requirements: Optional[Dict[str, Any]] = None
    min_score: Optional[float] = None
    salary_range: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    remote_allowed: bool = False
    job_type: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobUpdate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    employer_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Test Schemas
class TestQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_answer: Optional[str] = None
    question_type: str  # general, technical, role_specific

class TestSubmission(BaseModel):
    answers: Dict[str, str]  # question_id: answer

class TestResultResponse(BaseModel):
    id: int
    user_id: int
    test_type: str
    score: float
    max_score: float
    skills_score: Optional[float] = None
    test_score: Optional[float] = None
    negative_score: float = 0.0
    duration_minutes: Optional[int] = None
    completed_at: datetime
    
    class Config:
        from_attributes = True

# Application Schemas
class ApplicationBase(BaseModel):
    cover_letter: Optional[str] = None
    expected_salary: Optional[float] = None

class ApplicationCreate(ApplicationBase):
    job_id: int

class ApplicationResponse(ApplicationBase):
    id: int
    job_id: int
    applicant_id: int
    status: str
    match_score: Optional[float] = None
    test_score: Optional[float] = None
    applied_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Interview Schemas
class InterviewBase(BaseModel):
    scheduled_at: datetime
    duration_minutes: int = 60

class InterviewCreate(InterviewBase):
    application_id: int
    participant_id: int

class InterviewResponse(InterviewBase):
    id: int
    application_id: int
    participant_id: int
    room_id: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_url: Optional[str] = None
    facial_analysis: Optional[Dict[str, Any]] = None
    background_noise: bool = False
    cost_per_minute: float = 1.0
    total_cost: Optional[float] = None
    payment_status: str = "pending"
    created_at: datetime
    
    class Config:
        from_attributes = True

# Payment Schemas
class PaymentBase(BaseModel):
    amount: float
    currency: str = "USD"
    payment_method: str

class PaymentCreate(PaymentBase):
    interview_id: Optional[int] = None

class PaymentResponse(PaymentBase):
    id: int
    user_id: int
    interview_id: Optional[int] = None
    crypto_wallet_address: Optional[str] = None
    crypto_transaction_hash: Optional[str] = None
    crypto_amount: Optional[float] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Search Schemas
class JobSearch(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    remote_allowed: Optional[bool] = None
    job_type: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None

class CandidateSearch(BaseModel):
    skills: Optional[List[str]] = None
    min_score: Optional[float] = None
    location: Optional[str] = None
    remote_preference: Optional[bool] = None

# Response Schemas
class SuccessResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    detail: str 

# Government & Foreign Company Enhanced Schemas
class DocumentCreate(BaseModel):
    document_type: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    expires_at: Optional[datetime] = None
    access_level: str = "private"

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    document_type: str
    file_name: str
    file_size: int
    mime_type: str
    verification_status: str
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    encryption_hash: Optional[str] = None
    blockchain_hash: Optional[str] = None
    access_level: str
    uploaded_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

class ComplianceLogCreate(BaseModel):
    compliance_type: str
    requirements: Dict[str, Any]
    expires_at: Optional[datetime] = None

class ComplianceLogResponse(BaseModel):
    id: int
    user_id: int
    compliance_type: str
    status: str
    requirements: Dict[str, Any]
    verification_data: Optional[Dict[str, Any]] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CurrencyResponse(BaseModel):
    id: int
    code: str
    name: str
    symbol: Optional[str] = None
    exchange_rate_usd: float
    is_active: bool
    is_crypto: bool
    updated_at: datetime

    class Config:
        from_attributes = True

# Enhanced Profile Schemas
class GovernmentProfileUpdate(BaseModel):
    government_id: Optional[str] = None
    department: Optional[str] = None
    security_clearance_level: Optional[str] = None
    clearance_expiry_date: Optional[datetime] = None
    government_contracts: Optional[List[Dict[str, Any]]] = None

class ForeignCompanyProfileUpdate(BaseModel):
    country: Optional[str] = None
    business_license: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    legal_entity_type: Optional[str] = None
    foreign_currency_preference: Optional[str] = None
    international_compliance: Optional[Dict[str, Any]] = None
    visa_sponsorship_capability: Optional[bool] = None

class SecurityVerificationUpdate(BaseModel):
    identity_verified: Optional[bool] = None
    background_check_status: Optional[str] = None
    document_verification_status: Optional[str] = None
    facial_verification_status: Optional[str] = None

# Enhanced Job Schemas
class GovernmentJobCreate(BaseModel):
    title: str
    description: str
    requirements: Optional[Dict[str, Any]] = None
    min_score: Optional[float] = None
    salary_range: Optional[Dict[str, float]] = None
    location: Optional[str] = None
    remote_allowed: bool = False
    job_type: Optional[str] = None
    application_deadline: Optional[datetime] = None
    max_applications: Optional[int] = None
    security_clearance_required: Optional[str] = None
    government_contract_related: bool = False
    contract_number: Optional[str] = None
    compliance_requirements: Optional[Dict[str, Any]] = None

class ForeignCompanyJobCreate(BaseModel):
    title: str
    description: str
    requirements: Optional[Dict[str, Any]] = None
    min_score: Optional[float] = None
    salary_range: Optional[Dict[str, float]] = None
    location: Optional[str] = None
    remote_allowed: bool = False
    job_type: Optional[str] = None
    application_deadline: Optional[datetime] = None
    max_applications: Optional[int] = None
    visa_sponsorship_available: bool = False
    international_relocation: bool = False
    currency: str = "USD"
    tax_implications: Optional[Dict[str, Any]] = None

# Document Verification Schemas
class DocumentVerificationRequest(BaseModel):
    document_id: int
    verification_notes: Optional[str] = None
    status: str  # verified, rejected

class FacialVerificationRequest(BaseModel):
    user_id: int
    verification_image: str  # base64 encoded image
    verification_notes: Optional[str] = None

class ComplianceVerificationRequest(BaseModel):
    compliance_type: str
    verification_data: Dict[str, Any]
    review_notes: Optional[str] = None
    status: str  # compliant, non_compliant

# Multi-Currency Support
class CurrencyUpdate(BaseModel):
    exchange_rate_usd: float
    is_active: Optional[bool] = None

class SalaryConversionRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str

class SalaryConversionResponse(BaseModel):
    original_amount: float
    original_currency: str
    converted_amount: float
    converted_currency: str
    exchange_rate: float
    conversion_date: datetime 

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str  # email, realtime, system

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationUpdate(BaseModel):
    status: str = "read"  # unread, read, archived

class Notification(NotificationBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 