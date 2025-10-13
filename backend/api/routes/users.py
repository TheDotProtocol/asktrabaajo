from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from api.models.database import get_db, User, Profile, AuditLog
from api.models.schemas import ProfileCreate, ProfileUpdate, ProfileResponse
from api.routes.auth import get_current_user
from api.models.database import Job, Application, Interview, TestResult

router = APIRouter()

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile

@router.post("/profile", response_model=ProfileResponse)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update user profile."""
    # Check if profile already exists
    existing_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if existing_profile:
        # Update existing profile
        for field, value in profile_data.dict(exclude_unset=True).items():
            setattr(existing_profile, field, value)
        db.commit()
        db.refresh(existing_profile)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="profile_update",
            resource_type="profile",
            resource_id=existing_profile.id,
            ip_address="127.0.0.1",
            user_agent="API Client"
        )
        db.add(audit_log)
        db.commit()
        
        return existing_profile
    else:
        # Create new profile
        db_profile = Profile(
            user_id=current_user.id,
            **profile_data.dict()
        )
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="profile_create",
            resource_type="profile",
            resource_id=db_profile.id,
            ip_address="127.0.0.1",
            user_agent="API Client"
        )
        db.add(audit_log)
        db.commit()
        
        return db_profile

@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Update profile fields
    for field, value in profile_data.dict(exclude_unset=True).items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="profile_update",
        resource_type="profile",
        resource_id=profile.id,
        ip_address="127.0.0.1",
        user_agent="API Client"
    )
    db.add(audit_log)
    db.commit()
    
    return profile 

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for the current user"""
    try:
        stats = {
            "jobs": 0,
            "applications": 0,
            "interviews": 0,
            "assessments": 0
        }
        
        if current_user.role in ["employer", "consultant", "government", "foreign"]:
            # Count jobs posted by employer
            stats["jobs"] = db.query(Job).filter(Job.employer_id == current_user.id).count()
            
            # Count applications for employer's jobs
            stats["applications"] = db.query(Application).join(Job).filter(Job.employer_id == current_user.id).count()
            
            # Count interviews scheduled by employer
            stats["interviews"] = db.query(Interview).filter(Interview.employer_id == current_user.id).count()
            
        else:  # jobseeker
            # Count applications by jobseeker
            stats["applications"] = db.query(Application).filter(Application.jobseeker_id == current_user.id).count()
            
            # Count interviews for jobseeker
            stats["interviews"] = db.query(Interview).filter(Interview.jobseeker_id == current_user.id).count()
        
        # Count assessments for all users
        stats["assessments"] = db.query(TestResult).filter(TestResult.user_id == current_user.id).count()
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard stats: {str(e)}"
        ) 