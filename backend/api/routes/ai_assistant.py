from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from api.models.database import get_db, User
from api.routes.auth import get_current_user
from api.services.ai_service import AIService

router = APIRouter()
ai_service = AIService()

class ChatMessage(BaseModel):
    message: str
    context: Dict[str, Any] = None

class ChatResponse(BaseModel):
    response: str
    suggestions: list = []

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    chat_data: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat with the AI assistant."""
    try:
        # Prepare user context
        user_context = {
            "role": current_user.role,
            "page": chat_data.context.get("page", "unknown") if chat_data.context else "unknown",
            "actions": chat_data.context.get("actions", []) if chat_data.context else []
        }
        
        # Get AI response
        ai_response = await ai_service.chat_assistant(
            user_message=chat_data.message,
            user_context=user_context
        )
        
        # Generate suggestions based on user role and message
        suggestions = generate_suggestions(current_user.role, chat_data.message)
        
        return ChatResponse(
            response=ai_response,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with AI assistant: {str(e)}"
        )

@router.get("/suggestions")
async def get_ai_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered suggestions based on user role and context."""
    try:
        suggestions = generate_suggestions(current_user.role, "")
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating suggestions: {str(e)}"
        )

def generate_suggestions(user_role: str, message: str) -> list:
    """Generate contextual suggestions based on user role and message."""
    base_suggestions = {
        "jobseeker": [
            "How do I improve my profile?",
            "What skills are in demand?",
            "How do I prepare for video interviews?",
            "What should I include in my cover letter?",
            "How do I track my application status?"
        ],
        "employer": [
            "How do I write effective job descriptions?",
            "What are the best practices for candidate screening?",
            "How do I schedule video interviews?",
            "What questions should I ask in interviews?",
            "How do I evaluate candidate test results?"
        ],
        "consultant": [
            "How do I manage multiple client accounts?",
            "What are the latest hiring trends?",
            "How do I optimize job postings?",
            "What metrics should I track?",
            "How do I improve candidate matching?"
        ],
        "government": [
            "How do I ensure compliance in hiring?",
            "What documentation is required?",
            "How do I verify candidate credentials?",
            "What are the security requirements?",
            "How do I manage government contracts?"
        ],
        "foreign_company": [
            "How do I handle international hiring?",
            "What are the visa requirements?",
            "How do I manage currency conversions?",
            "What are the tax implications?",
            "How do I ensure legal compliance?"
        ]
    }
    
    # Get role-specific suggestions
    role_suggestions = base_suggestions.get(user_role, base_suggestions["jobseeker"])
    
    # Add general suggestions
    general_suggestions = [
        "How do I reset my password?",
        "What are the platform features?",
        "How do I contact support?",
        "What are the pricing plans?",
        "How do I update my profile?"
    ]
    
    # Combine and return suggestions
    all_suggestions = role_suggestions + general_suggestions
    
    # If there's a specific message, try to provide more targeted suggestions
    if message:
        message_lower = message.lower()
        if "interview" in message_lower:
            all_suggestions = [
                "How do I prepare for video interviews?",
                "What should I wear for interviews?",
                "How do I handle technical questions?",
                "What are common interview mistakes?",
                "How do I follow up after interviews?"
            ] + all_suggestions
        elif "test" in message_lower or "assessment" in message_lower:
            all_suggestions = [
                "How do I prepare for assessments?",
                "What types of questions are asked?",
                "How are test scores calculated?",
                "Can I retake assessments?",
                "How do I improve my test scores?"
            ] + all_suggestions
        elif "job" in message_lower or "apply" in message_lower:
            all_suggestions = [
                "How do I search for jobs?",
                "How do I apply for jobs?",
                "What should I include in applications?",
                "How do I track applications?",
                "How do I improve my job matches?"
            ] + all_suggestions
    
    return all_suggestions[:10]  # Return top 10 suggestions 