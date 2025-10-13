import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.database import Notification, User
from ..models.schemas import NotificationCreate, NotificationUpdate
import asyncio
import aiosmtplib
from jinja2 import Template

class NotificationService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@asktrabaajo.com")
        
    async def send_email_notification(
        self, 
        to_email: str, 
        subject: str, 
        template_name: str, 
        template_data: dict
    ) -> bool:
        """Send email notification using templates"""
        try:
            # Load email template
            template_content = self._get_email_template(template_name)
            template = Template(template_content)
            html_content = template.render(**template_data)
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=True
            )
            
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    def _get_email_template(self, template_name: str) -> str:
        """Get email template content"""
        templates = {
            "welcome": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #2563eb; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background: #f9fafb; }
                    .button { display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; }
                    .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to AskTrabaajo!</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {{first_name}}!</h2>
                        <p>Welcome to AskTrabaajo, the future of recruitment. Your account has been successfully created.</p>
                        <p><strong>Account Details:</strong></p>
                        <ul>
                            <li>Email: {{email}}</li>
                            <li>Role: {{role}}</li>
                            <li>Account Type: {{account_type}}</li>
                        </ul>
                        <p>Get started by completing your profile and exploring our AI-powered features.</p>
                        <a href="{{dashboard_url}}" class="button">Go to Dashboard</a>
                    </div>
                    <div class="footer">
                        <p>© 2024 AskTrabaajo. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            
            "job_application": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #10b981; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background: #f9fafb; }
                    .button { display: inline-block; padding: 12px 24px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; }
                    .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>New Job Application</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {{employer_name}}!</h2>
                        <p>You have received a new job application for the position of <strong>{{job_title}}</strong>.</p>
                        <p><strong>Applicant Details:</strong></p>
                        <ul>
                            <li>Name: {{applicant_name}}</li>
                            <li>Email: {{applicant_email}}</li>
                            <li>Assessment Score: {{assessment_score}}%</li>
                            <li>Applied: {{application_date}}</li>
                        </ul>
                        <a href="{{application_url}}" class="button">View Application</a>
                    </div>
                    <div class="footer">
                        <p>© 2024 AskTrabaajo. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            
            "interview_scheduled": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #f59e0b; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background: #f9fafb; }
                    .button { display: inline-block; padding: 12px 24px; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; }
                    .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Interview Scheduled</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {{participant_name}}!</h2>
                        <p>Your interview has been scheduled for the position of <strong>{{job_title}}</strong>.</p>
                        <p><strong>Interview Details:</strong></p>
                        <ul>
                            <li>Date: {{interview_date}}</li>
                            <li>Time: {{interview_time}}</li>
                            <li>Duration: {{duration}} minutes</li>
                            <li>Type: {{interview_type}}</li>
                        </ul>
                        <p>Please join the interview 5 minutes before the scheduled time.</p>
                        <a href="{{interview_url}}" class="button">Join Interview</a>
                    </div>
                    <div class="footer">
                        <p>© 2024 AskTrabaajo. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            
            "compliance_update": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #8b5cf6; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background: #f9fafb; }
                    .button { display: inline-block; padding: 12px 24px; background: #8b5cf6; color: white; text-decoration: none; border-radius: 6px; }
                    .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Compliance Status Update</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {{user_name}}!</h2>
                        <p>Your compliance status has been updated for <strong>{{compliance_type}}</strong>.</p>
                        <p><strong>Status Details:</strong></p>
                        <ul>
                            <li>Type: {{compliance_type}}</li>
                            <li>Status: {{status}}</li>
                            <li>Updated: {{update_date}}</li>
                            <li>Expires: {{expiry_date}}</li>
                        </ul>
                        <a href="{{compliance_url}}" class="button">View Details</a>
                    </div>
                    <div class="footer">
                        <p>© 2024 AskTrabaajo. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        return templates.get(template_name, templates["welcome"])
    
    def create_notification(
        self, 
        db: Session, 
        user_id: int, 
        title: str, 
        message: str, 
        notification_type: str = "realtime"
    ) -> Notification:
        """Create a new notification in the database"""
        notification_data = NotificationCreate(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type
        )
        
        db_notification = Notification(**notification_data.dict())
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
        
        return db_notification
    
    def get_user_notifications(
        self, 
        db: Session, 
        user_id: int, 
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user"""
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if status:
            query = query.filter(Notification.status == status)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    def mark_notification_read(
        self, 
        db: Session, 
        notification_id: int, 
        user_id: int
    ) -> Optional[Notification]:
        """Mark a notification as read"""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.status = "read"
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)
        
        return notification
    
    def mark_all_notifications_read(
        self, 
        db: Session, 
        user_id: int
    ) -> int:
        """Mark all notifications as read for a user"""
        result = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status == "unread"
        ).update({
            "status": "read",
            "read_at": datetime.utcnow()
        })
        
        db.commit()
        return result
    
    def get_unread_count(self, db: Session, user_id: int) -> int:
        """Get count of unread notifications for a user"""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status == "unread"
        ).count()
    
    async def send_welcome_email(self, user: User) -> bool:
        """Send welcome email to new user"""
        template_data = {
            "first_name": user.profile.first_name if user.profile else "User",
            "email": user.email,
            "role": user.role.title(),
            "account_type": "Premium" if user.role in ["government", "foreign"] else "Standard",
            "dashboard_url": "http://localhost:3001/dashboard"
        }
        
        return await self.send_email_notification(
            user.email,
            "Welcome to AskTrabaajo!",
            "welcome",
            template_data
        )
    
    async def send_job_application_email(
        self, 
        employer: User, 
        applicant: User, 
        job_title: str, 
        assessment_score: float
    ) -> bool:
        """Send job application notification email"""
        template_data = {
            "employer_name": employer.profile.first_name if employer.profile else "Employer",
            "job_title": job_title,
            "applicant_name": applicant.profile.first_name if applicant.profile else "Applicant",
            "applicant_email": applicant.email,
            "assessment_score": round(assessment_score, 1),
            "application_date": datetime.utcnow().strftime("%B %d, %Y"),
            "application_url": "http://localhost:3001/applications"
        }
        
        return await self.send_email_notification(
            employer.email,
            f"New Application for {job_title}",
            "job_application",
            template_data
        )
    
    async def send_interview_scheduled_email(
        self, 
        participant: User, 
        job_title: str, 
        interview_date: datetime, 
        duration: int,
        interview_url: str
    ) -> bool:
        """Send interview scheduled notification email"""
        template_data = {
            "participant_name": participant.profile.first_name if participant.profile else "Participant",
            "job_title": job_title,
            "interview_date": interview_date.strftime("%B %d, %Y"),
            "interview_time": interview_date.strftime("%I:%M %p"),
            "duration": duration,
            "interview_type": "Video Interview",
            "interview_url": interview_url
        }
        
        return await self.send_email_notification(
            participant.email,
            f"Interview Scheduled for {job_title}",
            "interview_scheduled",
            template_data
        )
    
    async def send_compliance_update_email(
        self, 
        user: User, 
        compliance_type: str, 
        status: str, 
        expiry_date: Optional[datetime] = None
    ) -> bool:
        """Send compliance status update email"""
        template_data = {
            "user_name": user.profile.first_name if user.profile else "User",
            "compliance_type": compliance_type,
            "status": status,
            "update_date": datetime.utcnow().strftime("%B %d, %Y"),
            "expiry_date": expiry_date.strftime("%B %d, %Y") if expiry_date else "N/A",
            "compliance_url": "http://localhost:3001/compliance"
        }
        
        return await self.send_email_notification(
            user.email,
            f"Compliance Update: {compliance_type}",
            "compliance_update",
            template_data
        ) 