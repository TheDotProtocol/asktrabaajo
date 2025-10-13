from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from api.models.database import get_db, User, Profile, AuditLog
from api.models.schemas import ProfileCreate, ProfileUpdate, ProfileResponse
from api.routes.auth import get_current_user

router = APIRouter()

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    for field, value in profile_data.dict(exclude_unset=True).items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="profile_updated",
        resource="profiles",
        details={}
    )
    db.add(audit_log)
    db.commit()
    
    return profile 