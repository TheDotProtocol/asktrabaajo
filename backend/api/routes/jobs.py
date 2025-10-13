from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.models.database import get_db, User, Job, Application, Profile, TestResult
from api.models.schemas import JobCreate, JobUpdate, JobResponse, ApplicationCreate, ApplicationResponse, JobSearch
from api.routes.auth import get_current_user
from api.services.ai_service import AIService

router = APIRouter()
ai_service = AIService()

@router.post("/", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job posting."""
    if current_user.role not in ["employer", "consultant", "government", "foreign_company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can post jobs"
        )
    
    db_job = Job(
        employer_id=current_user.id,
        **job_data.dict()
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return db_job

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all active jobs with optional filtering."""
    query = db.query(Job).filter(Job.status == "active")
    
    if search:
        query = query.filter(Job.title.ilike(f"%{search}%"))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if remote is not None:
        query = query.filter(Job.remote_allowed == remote)
    
    jobs = query.offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a specific job by ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a job posting."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.employer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this job"
        )
    
    for field, value in job_data.dict(exclude_unset=True).items():
        setattr(job, field, value)
    
    db.commit()
    db.refresh(job)
    return job

@router.get("/{job_id}/candidates", response_model=List[ApplicationResponse])
async def get_candidates(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get candidates for a specific job with AI-powered matching analysis."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.employer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view candidates for this job"
        )
    
    applications = db.query(Application).filter(Application.job_id == job_id).all()
    
    # Enhance applications with AI matching analysis
    enhanced_applications = []
    for application in applications:
        # Get candidate profile and test results
        candidate_profile = db.query(Profile).filter(Profile.user_id == application.applicant_id).first()
        latest_test = db.query(TestResult).filter(
            TestResult.user_id == application.applicant_id
        ).order_by(TestResult.created_at.desc()).first()
        
        # Prepare data for AI matching
        job_requirements = job.requirements or {}
        candidate_data = {
            'profile': candidate_profile.__dict__ if candidate_profile else {},
            'test_score': latest_test.score if latest_test else 0,
            'skills': candidate_profile.skills if candidate_profile else {},
            'experience': candidate_profile.experience if candidate_profile else {}
        }
        
        # Calculate AI-powered match score
        try:
            match_analysis = await ai_service.calculate_job_match(
                job_requirements=job_requirements,
                candidate_profile=candidate_data,
                test_score=latest_test.score if latest_test else 0
            )
            
            # Update application with AI insights
            application.match_score = match_analysis.get('match_score', application.match_score or 0)
            application.ai_analysis = match_analysis
            
        except Exception as e:
            # Fallback to basic matching
            if latest_test:
                application.match_score = (latest_test.score / latest_test.max_score) * 100
            else:
                application.match_score = 0
        
        enhanced_applications.append(application)
    
    # Sort by match score (highest first)
    enhanced_applications.sort(key=lambda x: x.match_score or 0, reverse=True)
    
    return enhanced_applications

@router.post("/{job_id}/apply", response_model=ApplicationResponse)
async def apply_for_job(
    job_id: int,
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply for a job with AI-powered matching."""
    if current_user.role != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can apply for jobs"
        )
    
    # Check if job exists and is active
    job = db.query(Job).filter(Job.id == job_id, Job.status == "active").first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not active"
        )
    
    # Check if already applied
    existing_application = db.query(Application).filter(
        Application.job_id == job_id,
        Application.applicant_id == current_user.id
    ).first()
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already applied for this job"
        )
    
    # Get user's profile and latest test score
    candidate_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    latest_test = db.query(TestResult).filter(
        TestResult.user_id == current_user.id
    ).order_by(TestResult.created_at.desc()).first()
    
    # Prepare candidate data for AI matching
    candidate_data = {
        'profile': candidate_profile.__dict__ if candidate_profile else {},
        'test_score': latest_test.score if latest_test else 0,
        'skills': candidate_profile.skills if candidate_profile else {},
        'experience': candidate_profile.experience if candidate_profile else {}
    }
    
    # Calculate AI-powered match score
    try:
        match_analysis = await ai_service.calculate_job_match(
            job_requirements=job.requirements or {},
            candidate_profile=candidate_data,
            test_score=latest_test.score if latest_test else 0
        )
        
        match_score = match_analysis.get('match_score', 0)
        ai_analysis = match_analysis
        
    except Exception as e:
        # Fallback to basic matching
        if latest_test:
            match_score = (latest_test.score / latest_test.max_score) * 100
        else:
            match_score = 0
        ai_analysis = {}
    
    db_application = Application(
        job_id=job_id,
        applicant_id=current_user.id,
        test_score=latest_test.score if latest_test else None,
        match_score=match_score,
        ai_analysis=ai_analysis,
        **application_data.dict()
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    return db_application

@router.get("/{job_id}/ai-recommendations")
async def get_ai_recommendations(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered job recommendations for job seekers."""
    if current_user.role != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can get recommendations"
        )
    
    # Get user's profile and test results
    candidate_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    latest_test = db.query(TestResult).filter(
        TestResult.user_id == current_user.id
    ).order_by(TestResult.created_at.desc()).first()
    
    # Get all active jobs
    active_jobs = db.query(Job).filter(Job.status == "active").all()
    
    # Calculate match scores for all jobs
    job_recommendations = []
    for job in active_jobs:
        candidate_data = {
            'profile': candidate_profile.__dict__ if candidate_profile else {},
            'test_score': latest_test.score if latest_test else 0,
            'skills': candidate_profile.skills if candidate_profile else {},
            'experience': candidate_profile.experience if candidate_profile else {}
        }
        
        try:
            match_analysis = await ai_service.calculate_job_match(
                job_requirements=job.requirements or {},
                candidate_profile=candidate_data,
                test_score=latest_test.score if latest_test else 0
            )
            
            job_recommendations.append({
                'job': job,
                'match_score': match_analysis.get('match_score', 0),
                'ai_analysis': match_analysis
            })
            
        except Exception as e:
            # Fallback scoring
            if latest_test:
                match_score = (latest_test.score / latest_test.max_score) * 100
            else:
                match_score = 0
            
            job_recommendations.append({
                'job': job,
                'match_score': match_score,
                'ai_analysis': {}
            })
    
    # Sort by match score (highest first) and return top 10
    job_recommendations.sort(key=lambda x: x['match_score'], reverse=True)
    
    return {
        'recommendations': job_recommendations[:10],
        'total_jobs_analyzed': len(active_jobs),
        'user_test_score': latest_test.score if latest_test else 0
    } 