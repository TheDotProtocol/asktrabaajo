from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from ..services.realtime_service import realtime_service
import json

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

@router.websocket("/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time notifications"""
    try:
        # Connect to real-time service
        await realtime_service.connect(websocket, user_id)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await realtime_service.send_personal_message({
                        "type": "pong",
                        "timestamp": "2024-12-19T10:00:00Z"
                    }, websocket)
                
                elif message.get("type") == "subscribe":
                    # Handle subscription to specific notification types
                    await realtime_service.send_personal_message({
                        "type": "subscribed",
                        "message": f"Subscribed to {message.get('channel', 'all')} notifications",
                        "timestamp": "2024-12-19T10:00:00Z"
                    }, websocket)
                
            except WebSocketDisconnect:
                realtime_service.disconnect(websocket)
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                await realtime_service.send_personal_message({
                    "type": "error",
                    "message": "An error occurred",
                    "timestamp": "2024-12-19T10:00:00Z"
                }, websocket)
                
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        realtime_service.disconnect(websocket)

@router.get("/status")
async def get_realtime_status():
    """Get real-time service status"""
    return {
        "connected_users": realtime_service.get_connected_users_count(),
        "total_connections": realtime_service.get_total_connections_count(),
        "status": "active"
    }

@router.post("/broadcast")
async def broadcast_message(message: dict):
    """Broadcast a message to all connected users (admin only)"""
    try:
        await realtime_service.broadcast_notification(message)
        return {"message": "Message broadcasted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")

@router.post("/send-to-user/{user_id}")
async def send_message_to_user(user_id: int, message: dict):
    """Send a message to a specific user (admin only)"""
    try:
        await realtime_service.send_notification_to_user(user_id, message)
        return {"message": f"Message sent to user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send failed: {str(e)}") 