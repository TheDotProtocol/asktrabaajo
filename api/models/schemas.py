from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    role: str

class UserCreate(UserBase):
    password: str
    first_name: str
    last_name: str

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

# Profile schemas
class ProfileBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    citizenship: Optional[str] = None
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    languages: List[Dict[str, Any]] = []
    certifications: List[Dict[str, Any]] = []
    work_experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    salary_expectation: Optional[float] = None
    availability: Optional[str] = None
    remote_preference: bool = False

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

# Job schemas
class JobBase(BaseModel):
    title: str
    description: str
    requirements: List[str] = []
    min_score_required: int = 0
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    location: Optional[str] = None
    is_remote: bool = False

class JobCreate(JobBase):
    pass

class JobUpdate(JobBase):
    is_active: Optional[bool] = None

class JobResponse(JobBase):
    id: int
    employer_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Test schemas
class TestQuestion(BaseModel):
    id: int
    question: str
    type: str  # multiple_choice, text, coding
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    points: int = 1

class TestSubmission(BaseModel):
    test_type: str
    answers: Dict[str, Any]
    duration_minutes: int

class TestResultResponse(BaseModel):
    id: int
    user_id: int
    test_type: str
    score: int
    max_score: int
    duration_minutes: int
    completed_at: datetime

    class Config:
        from_attributes = True

# Application schemas
class ApplicationBase(BaseModel):
    job_id: int

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: int
    jobseeker_id: int
    status: str
    applied_at: datetime

    class Config:
        from_attributes = True

# Interview schemas
class InterviewBase(BaseModel):
    application_id: int
    scheduled_at: datetime
    duration_minutes: int = 30

class InterviewCreate(InterviewBase):
    pass

class InterviewResponse(InterviewBase):
    id: int
    status: str
    room_id: Optional[str] = None
    recording_url: Optional[str] = None
    analysis_data: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True

# Payment schemas
class PaymentBase(BaseModel):
    amount: float
    currency: str = "USD"
    payment_method: str
    crypto_type: Optional[str] = None

class PaymentCreate(PaymentBase):
    interview_id: Optional[int] = None

class PaymentResponse(PaymentBase):
    id: int
    user_id: int
    interview_id: Optional[int] = None
    transaction_id: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Search and filter schemas
class JobSearch(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    remote_only: bool = False
    skills: Optional[List[str]] = None

class CandidateSearch(BaseModel):
    job_id: int
    min_score: Optional[int] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None

# Response schemas
class SuccessResponse(BaseModel):
    message: str
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None 