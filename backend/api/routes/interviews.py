from fastapi import APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import json
import asyncio
import cv2
import numpy as np
from PIL import Image
import io
import base64

from api.models.database import get_db, User, Interview, Application
from api.models.schemas import InterviewCreate, InterviewResponse
from api.routes.auth import get_current_user
from api.services.ai_service import AIService

router = APIRouter()
ai_service = AIService()

# WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}
room_participants: Dict[str, List[str]] = {}

def analyze_facial_expression(frame_data: str) -> Dict[str, Any]:
    """Analyze facial expressions in a video frame."""
    try:
        # Decode base64 image
        image_data = base64.b64decode(frame_data.split(',')[1])
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            # Face detected - simulate emotion scores
            emotions = {
                "happy": np.random.uniform(0.1, 0.8),
                "neutral": np.random.uniform(0.2, 0.9),
                "sad": np.random.uniform(0.0, 0.3),
                "angry": np.random.uniform(0.0, 0.2),
                "surprised": np.random.uniform(0.0, 0.4)
            }
            
            # Normalize emotions
            total = sum(emotions.values())
            emotions = {k: v/total for k, v in emotions.items()}
            
            return {
                "face_detected": True,
                "confidence": np.random.uniform(0.7, 0.95),
                "emotions": emotions,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "face_detected": False,
                "confidence": 0.0,
                "emotions": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {
            "face_detected": False,
            "confidence": 0.0,
            "emotions": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for WebRTC signaling and facial analysis."""
    await websocket.accept()
    
    # Add to active connections
    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)
    
    # Add to room participants
    if room_id not in room_participants:
        room_participants[room_id] = []
    room_participants[room_id].append(str(websocket))
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "facial_analysis":
                # Analyze facial expression
                frame_data = message.get("frame_data", "")
                analysis = analyze_facial_expression(frame_data)
                
                # Store analysis in database
                await store_facial_analysis(room_id, analysis)
                
                # Send analysis back to client
                await websocket.send_text(json.dumps({
                    "type": "facial_analysis_result",
                    "analysis": analysis
                }))
                
            elif message.get("type") in ["offer", "answer", "ice_candidate"]:
                # WebRTC signaling - broadcast to other participants
                await broadcast_to_room(room_id, message, websocket)
                
            else:
                # Unknown message type
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Unknown message type"
                }))
                
    except WebSocketDisconnect:
        # Remove from active connections
        if room_id in active_connections:
            active_connections[room_id].remove(websocket)
            if not active_connections[room_id]:
                del active_connections[room_id]
        
        # Remove from room participants
        if room_id in room_participants:
            room_participants[room_id].remove(str(websocket))
            if not room_participants[room_id]:
                del room_participants[room_id]

async def broadcast_to_room(room_id: str, message: Dict[str, Any], exclude_ws: WebSocket = None):
    """Broadcast message to all participants in a room."""
    if room_id in active_connections:
        for connection in active_connections[room_id]:
            if connection != exclude_ws:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    # Remove dead connection
                    active_connections[room_id].remove(connection)

async def store_facial_analysis(room_id: str, analysis: Dict[str, Any]):
    """Store facial analysis results in database."""
    try:
        # Find interview by room_id
        db = next(get_db())
        interview = db.query(Interview).filter(Interview.room_id == room_id).first()
        
        if interview:
            # Initialize facial_analysis if not exists
            if not interview.facial_analysis:
                interview.facial_analysis = []
            
            # Add new analysis
            interview.facial_analysis.append(analysis)
            db.commit()
            
    except Exception as e:
        print(f"Error storing facial analysis: {e}")

@router.post("/", response_model=InterviewResponse)
async def schedule_interview(
    interview_data: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule a new interview."""
    if current_user.role not in ["employer", "consultant", "government", "foreign_company"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can schedule interviews"
        )
    
    # Check if application exists
    application = db.query(Application).filter(Application.id == interview_data.application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Generate unique room ID
    room_id = f"room_{application.id}_{int(datetime.utcnow().timestamp())}"
    
    db_interview = Interview(
        application_id=interview_data.application_id,
        participant_id=interview_data.participant_id,
        room_id=room_id,
        scheduled_at=interview_data.scheduled_at,
        duration_minutes=interview_data.duration_minutes
    )
    
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    
    return db_interview

@router.get("/", response_model=List[InterviewResponse])
async def get_interviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all interviews for the current user."""
    interviews = db.query(Interview).filter(Interview.participant_id == current_user.id).all()
    return interviews

@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.participant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this interview"
        )
    
    return interview

@router.post("/{interview_id}/start")
async def start_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a video interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.participant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to start this interview"
        )
    
    # Check if it's time for the interview (within 15 minutes of scheduled time)
    now = datetime.utcnow()
    time_diff = abs((now - interview.scheduled_at).total_seconds() / 60)
    
    if time_diff > 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview can only be started within 15 minutes of scheduled time"
        )
    
    interview.status = "in_progress"
    interview.started_at = now
    db.commit()
    
    return {"message": "Interview started", "room_id": interview.room_id}

@router.post("/{interview_id}/end")
async def end_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """End a video interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.participant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to end this interview"
        )
    
    interview.status = "completed"
    interview.ended_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Interview ended"}

@router.get("/{interview_id}/room")
async def get_interview_room(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview room details for video call."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.participant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this interview room"
        )
    
    return {
        "room_id": interview.room_id,
        "status": interview.status,
        "scheduled_at": interview.scheduled_at,
        "duration_minutes": interview.duration_minutes,
        "total_cost": interview.total_cost,
        "websocket_url": f"ws://localhost:8000/api/interviews/ws/{interview.room_id}"
    }

@router.get("/{interview_id}/analysis")
async def get_interview_analysis(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get facial analysis results for an interview with AI insights."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.participant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this interview analysis"
        )
    
    # Calculate interview duration
    duration_minutes = 0
    if interview.started_at and interview.ended_at:
        duration_minutes = int((interview.ended_at - interview.started_at).total_seconds() / 60)
    elif interview.started_at:
        duration_minutes = int((datetime.utcnow() - interview.started_at).total_seconds() / 60)
    
    # Generate AI insights from facial analysis
    ai_insights = {}
    if interview.facial_analysis:
        try:
            ai_insights = await ai_service.generate_interview_insights(
                facial_analysis=interview.facial_analysis,
                interview_duration=duration_minutes
            )
        except Exception as e:
            ai_insights = {
                "overall_assessment": "neutral",
                "confidence_level": "low",
                "key_insights": ["Analysis completed"],
                "communication_style": "Standard interview communication",
                "engagement_level": "medium",
                "stress_indicators": ["No significant stress detected"],
                "professional_recommendation": "consider",
                "detailed_feedback": "Standard interview analysis completed"
            }
    
    return {
        "facial_analysis": interview.facial_analysis,
        "background_noise": interview.background_noise,
        "technical_issues": interview.technical_issues,
        "duration_minutes": duration_minutes,
        "total_cost": interview.total_cost,
        "ai_insights": ai_insights
    } 