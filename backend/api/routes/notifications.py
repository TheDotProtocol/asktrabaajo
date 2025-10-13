from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..models.database import get_db, User
from ..models.schemas import Notification, NotificationUpdate
from ..services.notification_service import NotificationService
from ..routes.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("/", response_model=List[Notification])
async def get_notifications(
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user notifications"""
    notification_service = NotificationService()
    notifications = notification_service.get_user_notifications(
        db, current_user.id, status, limit
    )
    return notifications

@router.get("/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of unread notifications"""
    notification_service = NotificationService()
    count = notification_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    notification_service = NotificationService()
    notification = notification_service.mark_notification_read(
        db, notification_id, current_user.id
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}

@router.put("/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read"""
    notification_service = NotificationService()
    count = notification_service.mark_all_notifications_read(db, current_user.id)
    return {"message": f"{count} notifications marked as read"}

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted"}

@router.post("/test-email")
async def test_email_notification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test email notification (for development)"""
    notification_service = NotificationService()
    
    # Send welcome email as test
    success = await notification_service.send_welcome_email(current_user)
    
    if success:
        return {"message": "Test email sent successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test email"
        ) 