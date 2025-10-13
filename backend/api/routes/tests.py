from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
import random

from api.models.database import get_db, User, TestResult, Job
from api.models.schemas import TestQuestion, TestSubmission, TestResultResponse
from api.routes.auth import get_current_user
from api.services.ai_service import AIService

router = APIRouter()
ai_service = AIService()

# Sample questions (fallback when AI is unavailable)
GENERAL_QUESTIONS = [
    {
        "id": 1,
        "question": "How do you handle tight deadlines?",
        "options": ["I thrive under pressure", "I prefer to plan ahead", "I get stressed but manage", "I avoid them"],
        "question_type": "general"
    },
    {
        "id": 2,
        "question": "What motivates you most in a work environment?",
        "options": ["Recognition and praise", "Financial rewards", "Learning new skills", "Helping others"],
        "question_type": "general"
    },
    {
        "id": 3,
        "question": "How do you prefer to work in a team?",
        "options": ["As a leader", "As a collaborator", "Independently", "Supporting others"],
        "question_type": "general"
    }
]

TECHNICAL_QUESTIONS = [
    {
        "id": 4,
        "question": "What is the time complexity of binary search?",
        "options": ["O(1)", "O(log n)", "O(n)", "O(n²)"],
        "correct_answer": "O(log n)",
        "question_type": "technical"
    },
    {
        "id": 5,
        "question": "Which data structure uses LIFO?",
        "options": ["Queue", "Stack", "Tree", "Graph"],
        "correct_answer": "Stack",
        "question_type": "technical"
    }
]

@router.get("/questions", response_model=List[TestQuestion])
async def get_test_questions(
    test_type: str = "general",
    job_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated test questions for the user."""
    if current_user.role != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can take tests"
        )
    
    # Get job context if job_id is provided
    job_title = None
    skills = None
    if job_id:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job_title = job.title
            if job.requirements:
                skills = job.requirements.get('skills', [])
    
    # Generate AI-powered questions
    try:
        questions = await ai_service.generate_test_questions(
            test_type=test_type,
            job_title=job_title,
            skills=skills
        )
        
        # If AI generation fails or returns too few questions, use fallback
        if len(questions) < 10:
            if test_type == "general":
                questions = GENERAL_QUESTIONS
            elif test_type == "technical":
                questions = TECHNICAL_QUESTIONS
            else:
                questions = GENERAL_QUESTIONS + TECHNICAL_QUESTIONS
            
            # Randomize and limit to 20 questions
            random.shuffle(questions)
            questions = questions[:20]
        
        return [TestQuestion(**q) for q in questions]
        
    except Exception as e:
        # Fallback to sample questions
        if test_type == "general":
            questions = GENERAL_QUESTIONS
        elif test_type == "technical":
            questions = TECHNICAL_QUESTIONS
        else:
            questions = GENERAL_QUESTIONS + TECHNICAL_QUESTIONS
        
        # Randomize and limit to 20 questions
        random.shuffle(questions)
        questions = questions[:20]
        
        return [TestQuestion(**q) for q in questions]

@router.post("/submit", response_model=TestResultResponse)
async def submit_test(
    submission: TestSubmission,
    test_type: str = "general",
    job_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit test answers and get AI-powered results."""
    if current_user.role != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can take tests"
        )
    
    # Get the questions that were used for this test
    questions = []
    if test_type == "general":
        questions = GENERAL_QUESTIONS
    elif test_type == "technical":
        questions = TECHNICAL_QUESTIONS
    else:
        questions = GENERAL_QUESTIONS + TECHNICAL_QUESTIONS
    
    # Filter questions to only include those that were answered
    answered_questions = []
    for q in questions:
        if str(q['id']) in submission.answers:
            answered_questions.append(q)
    
    # Use AI to analyze answers
    try:
        ai_analysis = await ai_service.analyze_test_answers(
            questions=answered_questions,
            answers=submission.answers,
            test_type=test_type
        )
        
        # Extract scores from AI analysis
        overall_score = ai_analysis.get('overall_score', 0)
        skills_score = ai_analysis.get('skills_score', 0)
        test_score = ai_analysis.get('test_score', 0)
        
        # Store AI insights
        ai_insights = {
            'strengths': ai_analysis.get('strengths', []),
            'weaknesses': ai_analysis.get('weaknesses', []),
            'detailed_feedback': ai_analysis.get('detailed_feedback', ''),
            'recommendations': ai_analysis.get('recommendations', [])
        }
        
    except Exception as e:
        # Fallback to basic scoring
        total_questions = len(submission.answers)
        correct_answers = 0
        
        if test_type == "technical":
            for question_id, answer in submission.answers.items():
                for q in TECHNICAL_QUESTIONS:
                    if str(q["id"]) == question_id and q.get("correct_answer") == answer:
                        correct_answers += 1
                        break
        else:
            for question_id, answer in submission.answers.items():
                if answer in ["I thrive under pressure", "Learning new skills", "As a collaborator"]:
                    correct_answers += 1
                else:
                    correct_answers += 0.5
        
        overall_score = (correct_answers / total_questions) * 20 if total_questions > 0 else 0
        skills_score = overall_score * 0.5
        test_score = overall_score * 0.5
        
        ai_insights = {
            'strengths': ['Good understanding of basic concepts'],
            'weaknesses': ['Could improve in some areas'],
            'detailed_feedback': 'Standard assessment completed',
            'recommendations': ['Continue learning and practicing']
        }
    
    # Create test result
    db_test_result = TestResult(
        user_id=current_user.id,
        test_type=test_type,
        questions=answered_questions,  # Store as JSON
        answers=submission.answers,
        score=overall_score,
        max_score=20.0,
        skills_score=skills_score,
        test_score=test_score,
        duration_minutes=30,  # Placeholder
        ai_insights=ai_insights  # Store AI analysis
    )
    
    db.add(db_test_result)
    db.commit()
    db.refresh(db_test_result)
    
    return db_test_result

@router.get("/results", response_model=List[TestResultResponse])
async def get_test_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's test results with AI insights."""
    results = db.query(TestResult).filter(
        TestResult.user_id == current_user.id
    ).order_by(TestResult.created_at.desc()).all()
    
    return results

@router.get("/ai-insights/{test_result_id}")
async def get_ai_insights(
    test_result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed AI insights for a specific test result."""
    test_result = db.query(TestResult).filter(
        TestResult.id == test_result_id,
        TestResult.user_id == current_user.id
    ).first()
    
    if not test_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test result not found"
        )
    
    return {
        "test_result_id": test_result.id,
        "score": test_result.score,
        "ai_insights": test_result.ai_insights if hasattr(test_result, 'ai_insights') else {},
        "test_type": test_result.test_type,
        "completed_at": test_result.completed_at
    } 