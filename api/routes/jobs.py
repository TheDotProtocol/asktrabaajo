from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.models.database import get_db, User, Job, Profile, Application, TestResult
from api.models.schemas import JobCreate, JobUpdate, JobResponse, JobSearch, CandidateSearch
from api.routes.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["employer", "consultant", "government", "foreign_company"]:
        raise HTTPException(status_code=403, detail="Only employers can post jobs")
    
    job = Job(**job_data.dict(), employer_id=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    location: Optional[str] = None,
    remote_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Job).filter(Job.is_active == True)
    
    if search:
        query = query.filter(Job.title.contains(search) | Job.description.contains(search))
    if location:
        query = query.filter(Job.location.contains(location))
    if remote_only:
        query = query.filter(Job.is_remote == True)
    
    jobs = query.offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    for field, value in job_data.dict(exclude_unset=True).items():
        setattr(job, field, value)
    
    db.commit()
    db.refresh(job)
    return job

@router.get("/{job_id}/candidates")
async def get_candidates(
    job_id: int,
    min_score: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify job exists and user owns it
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get candidates who applied and meet score requirements
    query = db.query(Profile, TestResult).join(TestResult, Profile.user_id == TestResult.user_id)
    
    if min_score:
        query = query.filter(TestResult.score >= min_score)
    else:
        query = query.filter(TestResult.score >= job.min_score_required)
    
    candidates = query.all()
    
    # Format response
    result = []
    for profile, test_result in candidates:
        result.append({
            "profile": {
                "id": profile.id,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "technical_skills": profile.technical_skills,
                "soft_skills": profile.soft_skills,
                "location": profile.location,
                "salary_expectation": profile.salary_expectation
            },
            "test_score": test_result.score,
            "test_type": test_result.test_type
        })
    
    return result 