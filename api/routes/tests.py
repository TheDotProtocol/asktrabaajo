from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import random

from api.models.database import get_db, User, TestResult, Profile, AuditLog
from api.models.schemas import TestSubmission, TestResultResponse
from api.routes.auth import get_current_user

router = APIRouter()

# Sample questions for different test types
GENERAL_QUESTIONS = [
    {
        "id": 1,
        "question": "How do you handle stress in a professional environment?",
        "type": "multiple_choice",
        "options": ["Avoid it", "Take breaks", "Delegate tasks", "Face it head-on"],
        "points": 1
    },
    {
        "id": 2,
        "question": "Describe a time when you had to work with a difficult team member.",
        "type": "text",
        "points": 1
    },
    {
        "id": 3,
        "question": "What motivates you to perform at your best?",
        "type": "multiple_choice",
        "options": ["Money", "Recognition", "Learning", "Helping others"],
        "points": 1
    },
    {
        "id": 4,
        "question": "How do you prioritize multiple deadlines?",
        "type": "text",
        "points": 1
    },
    {
        "id": 5,
        "question": "What's your approach to learning new skills?",
        "type": "multiple_choice",
        "options": ["Self-study", "Formal training", "Mentorship", "Hands-on practice"],
        "points": 1
    }
]

TECHNICAL_QUESTIONS = {
    "software_engineer": [
        {
            "id": 6,
            "question": "Explain the difference between REST and GraphQL APIs.",
            "type": "text",
            "points": 1
        },
        {
            "id": 7,
            "question": "What is the time complexity of binary search?",
            "type": "multiple_choice",
            "options": ["O(1)", "O(log n)", "O(n)", "O(n²)"],
            "points": 1
        },
        {
            "id": 8,
            "question": "How would you debug a production issue?",
            "type": "text",
            "points": 1
        }
    ],
    "data_scientist": [
        {
            "id": 9,
            "question": "Explain the difference between supervised and unsupervised learning.",
            "type": "text",
            "points": 1
        },
        {
            "id": 10,
            "question": "What is overfitting in machine learning?",
            "type": "text",
            "points": 1
        }
    ]
}

@router.get("/questions/{test_type}")
async def get_test_questions(
    test_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get 20 questions for the test (10 general + 10 role-specific)"""
    
    # Check if user already has a test result
    existing_test = db.query(TestResult).filter(
        TestResult.user_id == current_user.id,
        TestResult.test_type == test_type
    ).first()
    
    if existing_test:
        raise HTTPException(status_code=400, detail="Test already completed")
    
    # Get user's profile to determine role-specific questions
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    # Select 10 general questions
    general_questions = random.sample(GENERAL_QUESTIONS, 10)
    
    # Select 10 role-specific questions
    role_questions = []
    if test_type == "technical":
        # Determine role from profile skills
        if profile and profile.technical_skills:
            for skill in profile.technical_skills:
                if "python" in skill.lower() or "javascript" in skill.lower():
                    role_questions = TECHNICAL_QUESTIONS.get("software_engineer", [])
                    break
                elif "machine learning" in skill.lower() or "data" in skill.lower():
                    role_questions = TECHNICAL_QUESTIONS.get("data_scientist", [])
                    break
        
        # If no specific role found, use software engineer questions
        if not role_questions:
            role_questions = TECHNICAL_QUESTIONS.get("software_engineer", [])
    
    # Combine questions (ensure we have 20 total)
    all_questions = general_questions + role_questions[:10]
    
    # Shuffle questions
    random.shuffle(all_questions)
    
    return {
        "test_type": test_type,
        "total_questions": len(all_questions),
        "questions": all_questions
    }

@router.post("/submit", response_model=TestResultResponse)
async def submit_test(
    test_data: TestSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit test answers and calculate score"""
    
    # Check if test already completed
    existing_test = db.query(TestResult).filter(
        TestResult.user_id == current_user.id,
        TestResult.test_type == test_data.test_type
    ).first()
    
    if existing_test:
        raise HTTPException(status_code=400, detail="Test already completed")
    
    # Calculate score (simplified scoring algorithm)
    score = 0
    total_questions = len(test_data.answers)
    
    # Simple scoring: 1 point per answered question (we'll improve this later)
    score = min(total_questions, 20)  # Cap at 20
    
    # Create test result
    test_result = TestResult(
        user_id=current_user.id,
        test_type=test_data.test_type,
        score=score,
        max_score=20,
        answers=test_data.answers,
        duration_minutes=test_data.duration_minutes
    )
    
    db.add(test_result)
    db.commit()
    db.refresh(test_result)
    
    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="test_completed",
        resource="tests",
        details={"test_type": test_data.test_type, "score": score}
    )
    db.add(audit_log)
    db.commit()
    
    return test_result

@router.get("/results", response_model=List[TestResultResponse])
async def get_test_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's test results"""
    results = db.query(TestResult).filter(TestResult.user_id == current_user.id).all()
    return results

@router.get("/results/{test_id}", response_model=TestResultResponse)
async def get_test_result(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific test result"""
    result = db.query(TestResult).filter(
        TestResult.id == test_id,
        TestResult.user_id == current_user.id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    return result 