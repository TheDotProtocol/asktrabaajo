import json
import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

class RealtimeNotificationService:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect a user to the real-time notification service"""
        await websocket.accept()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        
        self.user_connections[user_id].add(websocket)
        self.active_connections[id(websocket)] = user_id
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to real-time notifications",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a user from the real-time notification service"""
        websocket_id = id(websocket)
        if websocket_id in self.active_connections:
            user_id = self.active_connections[websocket_id]
            del self.active_connections[websocket_id]
            
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def send_notification_to_user(self, user_id: int, notification: dict):
        """Send a notification to all connections of a specific user"""
        if user_id in self.user_connections:
            disconnected_websockets = set()
            
            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "notification",
                        "data": notification,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception as e:
                    print(f"Error sending notification to user {user_id}: {e}")
                    disconnected_websockets.add(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected_websockets:
                self.disconnect(websocket)
    
    async def broadcast_notification(self, notification: dict, user_ids: list = None):
        """Broadcast a notification to multiple users or all users"""
        if user_ids:
            for user_id in user_ids:
                await self.send_notification_to_user(user_id, notification)
        else:
            # Broadcast to all connected users
            for user_id in list(self.user_connections.keys()):
                await self.send_notification_to_user(user_id, notification)
    
    async def send_system_message(self, message: str, user_ids: list = None):
        """Send a system message to users"""
        system_message = {
            "type": "system",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_ids:
            for user_id in user_ids:
                await self.send_notification_to_user(user_id, system_message)
        else:
            await self.broadcast_notification(system_message)
    
    async def send_job_application_notification(self, employer_id: int, applicant_name: str, job_title: str):
        """Send job application notification to employer"""
        notification = {
            "type": "job_application",
            "title": "New Job Application",
            "message": f"New application for {job_title} from {applicant_name}",
            "data": {
                "job_title": job_title,
                "applicant_name": applicant_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.send_notification_to_user(employer_id, notification)
    
    async def send_interview_scheduled_notification(self, user_id: int, job_title: str, interview_date: str):
        """Send interview scheduled notification"""
        notification = {
            "type": "interview_scheduled",
            "title": "Interview Scheduled",
            "message": f"Interview scheduled for {job_title} on {interview_date}",
            "data": {
                "job_title": job_title,
                "interview_date": interview_date,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.send_notification_to_user(user_id, notification)
    
    async def send_assessment_completed_notification(self, user_id: int, score: float, job_title: str = None):
        """Send assessment completed notification"""
        message = f"Assessment completed with score: {score}%"
        if job_title:
            message += f" for {job_title}"
        
        notification = {
            "type": "assessment_completed",
            "title": "Assessment Completed",
            "message": message,
            "data": {
                "score": score,
                "job_title": job_title,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.send_notification_to_user(user_id, notification)
    
    async def send_compliance_update_notification(self, user_id: int, compliance_type: str, status: str):
        """Send compliance update notification"""
        notification = {
            "type": "compliance_update",
            "title": "Compliance Update",
            "message": f"{compliance_type} status updated to: {status}",
            "data": {
                "compliance_type": compliance_type,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.send_notification_to_user(user_id, notification)
    
    async def send_payment_notification(self, user_id: int, amount: float, currency: str, status: str):
        """Send payment notification"""
        notification = {
            "type": "payment",
            "title": "Payment Update",
            "message": f"Payment of {amount} {currency} {status}",
            "data": {
                "amount": amount,
                "currency": currency,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.send_notification_to_user(user_id, notification)
    
    def get_connected_users_count(self) -> int:
        """Get the number of currently connected users"""
        return len(self.user_connections)
    
    def get_total_connections_count(self) -> int:
        """Get the total number of active connections"""
        return len(self.active_connections)

# Global instance
realtime_service = RealtimeNotificationService() 