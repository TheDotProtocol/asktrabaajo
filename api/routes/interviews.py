from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime, timedelta

from api.models.database import get_db, User, Interview, Application, AuditLog, Job
from api.models.schemas import InterviewCreate, InterviewResponse
from api.routes.auth import get_current_user

router = APIRouter()

@router.post("/schedule", response_model=InterviewResponse)
async def schedule_interview(
    interview_data: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule an interview for an application"""
    
    # Verify application exists and user has permission
    application = db.query(Application).filter(Application.id == interview_data.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check if user is the employer for this application
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if job.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to schedule interview for this application")
    
    # Check if interview already exists
    existing_interview = db.query(Interview).filter(
        Interview.application_id == interview_data.application_id
    ).first()
    
    if existing_interview:
        raise HTTPException(status_code=400, detail="Interview already scheduled for this application")
    
    # Generate unique room ID
    room_id = f"interview_{uuid.uuid4().hex[:8]}"
    
    # Create interview
    interview = Interview(
        application_id=interview_data.application_id,
        scheduled_at=interview_data.scheduled_at,
        duration_minutes=interview_data.duration_minutes,
        room_id=room_id,
        status="scheduled"
    )
    
    db.add(interview)
    db.commit()
    db.refresh(interview)
    
    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="interview_scheduled",
        resource="interviews",
        details={"application_id": interview_data.application_id, "room_id": room_id}
    )
    db.add(audit_log)
    db.commit()
    
    return interview

@router.get("/", response_model=List[InterviewResponse])
async def get_interviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's interviews (as employer or jobseeker)"""
    
    if current_user.role == "jobseeker":
        # Get interviews for applications by this jobseeker
        interviews = db.query(Interview).join(Application).filter(
            Application.jobseeker_id == current_user.id
        ).all()
    else:
        # Get interviews for jobs posted by this employer
        interviews = db.query(Interview).join(Application).join(Job).filter(
            Job.employer_id == current_user.id
        ).all()
    
    return interviews

@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific interview details"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Check if user has permission to view this interview
    application = db.query(Application).filter(Application.id == interview.application_id).first()
    job = db.query(Job).filter(Job.id == application.job_id).first()
    
    if current_user.role == "jobseeker":
        if application.jobseeker_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this interview")
    else:
        if job.employer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this interview")
    
    return interview

@router.put("/{interview_id}/start")
async def start_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start an interview"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Check if it's time to start (within 5 minutes of scheduled time)
    now = datetime.utcnow()
    time_diff = abs((interview.scheduled_at - now).total_seconds() / 60)
    
    if time_diff > 5:
        raise HTTPException(status_code=400, detail="Interview can only be started within 5 minutes of scheduled time")
    
    interview.status = "in_progress"
    db.commit()
    
    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="interview_started",
        resource="interviews",
        details={"interview_id": interview_id}
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Interview started", "room_id": interview.room_id}

@router.put("/{interview_id}/end")
async def end_interview(
    interview_id: int,
    analysis_data: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """End an interview and save analysis data"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    interview.status = "completed"
    if analysis_data:
        interview.analysis_data = analysis_data
    
    db.commit()
    
    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="interview_completed",
        resource="interviews",
        details={"interview_id": interview_id}
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Interview completed"}

@router.get("/{interview_id}/room")
async def get_interview_room(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview room details for video call"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Check permissions
    application = db.query(Application).filter(Application.id == interview.application_id).first()
    job = db.query(Job).filter(Job.id == application.job_id).first()
    
    if current_user.role == "jobseeker":
        if application.jobseeker_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if job.employer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "room_id": interview.room_id,
        "status": interview.status,
        "scheduled_at": interview.scheduled_at,
        "duration_minutes": interview.duration_minutes
    } 