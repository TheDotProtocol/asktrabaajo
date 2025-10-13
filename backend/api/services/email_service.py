import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import os
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@asktrabaajo.com")
        self.from_name = os.getenv("FROM_NAME", "AskTrabaajo")
        
        # Email templates directory
        self.templates_dir = Path("email_templates")
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates if they don't exist."""
        templates = {
            "welcome.html": self._get_welcome_template(),
            "job_application.html": self._get_job_application_template(),
            "interview_scheduled.html": self._get_interview_scheduled_template(),
            "interview_reminder.html": self._get_interview_reminder_template(),
            "compliance_update.html": self._get_compliance_update_template(),
            "test_completed.html": self._get_test_completed_template(),
            "profile_verified.html": self._get_profile_verified_template(),
            "password_reset.html": self._get_password_reset_template()
        }
        
        for filename, content in templates.items():
            template_path = self.templates_dir / filename
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        text_content: str = None,
        attachments: List[Dict] = None
    ) -> bool:
        """Send an email with HTML content."""
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP credentials not configured, email not sent")
                return False
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    self._add_attachment(message, attachment)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def _add_attachment(self, message: MIMEMultipart, attachment: Dict):
        """Add attachment to email message."""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['data'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            message.attach(part)
        except Exception as e:
            logger.error(f"Error adding attachment: {e}")
    
    async def send_welcome_email(self, user_email: str, user_name: str, role: str) -> bool:
        """Send welcome email to new users."""
        try:
            template_path = self.templates_dir / "welcome.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            html_content = template.format(
                user_name=user_name,
                role=role.title(),
                current_year=datetime.now().year
            )
            
            subject = f"Welcome to AskTrabaajo, {user_name}!"
            text_content = f"Welcome to AskTrabaajo! We're excited to have you on board as a {role}."
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False
    
    async def send_job_application_email(
        self, 
        user_email: str, 
        user_name: str, 
        job_title: str, 
        company_name: str,
        application_id: int
    ) -> bool:
        """Send job application confirmation email."""
        try:
            template_path = self.templates_dir / "job_application.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            html_content = template.format(
                user_name=user_name,
                job_title=job_title,
                company_name=company_name,
                application_id=application_id,
                current_year=datetime.now().year
            )
            
            subject = f"Application Submitted: {job_title} at {company_name}"
            text_content = f"Your application for {job_title} at {company_name} has been submitted successfully."
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending job application email: {e}")
            return False
    
    async def send_interview_scheduled_email(
        self, 
        user_email: str, 
        user_name: str, 
        job_title: str, 
        company_name: str,
        interview_date: datetime,
        room_id: str
    ) -> bool:
        """Send interview scheduling email."""
        try:
            template_path = self.templates_dir / "interview_scheduled.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            formatted_date = interview_date.strftime("%B %d, %Y at %I:%M %p")
            
            html_content = template.format(
                user_name=user_name,
                job_title=job_title,
                company_name=company_name,
                interview_date=formatted_date,
                room_id=room_id,
                current_year=datetime.now().year
            )
            
            subject = f"Interview Scheduled: {job_title} at {company_name}"
            text_content = f"Your interview for {job_title} at {company_name} has been scheduled for {formatted_date}."
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending interview scheduled email: {e}")
            return False
    
    async def send_interview_reminder_email(
        self, 
        user_email: str, 
        user_name: str, 
        job_title: str, 
        company_name: str,
        interview_date: datetime,
        room_id: str
    ) -> bool:
        """Send interview reminder email."""
        try:
            template_path = self.templates_dir / "interview_reminder.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            formatted_date = interview_date.strftime("%B %d, %Y at %I:%M %p")
            
            html_content = template.format(
                user_name=user_name,
                job_title=job_title,
                company_name=company_name,
                interview_date=formatted_date,
                room_id=room_id,
                current_year=datetime.now().year
            )
            
            subject = f"Interview Reminder: {job_title} at {company_name}"
            text_content = f"Reminder: Your interview for {job_title} at {company_name} is scheduled for {formatted_date}."
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending interview reminder email: {e}")
            return False
    
    async def send_compliance_update_email(
        self, 
        user_email: str, 
        user_name: str, 
        compliance_type: str, 
        status: str,
        details: str = None
    ) -> bool:
        """Send compliance status update email."""
        try:
            template_path = self.templates_dir / "compliance_update.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            html_content = template.format(
                user_name=user_name,
                compliance_type=compliance_type.replace('_', ' ').title(),
                status=status.title(),
                details=details or "No additional details provided.",
                current_year=datetime.now().year
            )
            
            subject = f"Compliance Update: {compliance_type.replace('_', ' ').title()}"
            text_content = f"Your {compliance_type} compliance status has been updated to: {status}"
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending compliance update email: {e}")
            return False
    
    async def send_test_completed_email(
        self, 
        user_email: str, 
        user_name: str, 
        test_type: str, 
        score: float,
        max_score: float = 20.0
    ) -> bool:
        """Send test completion email."""
        try:
            template_path = self.templates_dir / "test_completed.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            percentage = (score / max_score) * 100
            
            html_content = template.format(
                user_name=user_name,
                test_type=test_type.replace('_', ' ').title(),
                score=score,
                max_score=max_score,
                percentage=f"{percentage:.1f}%",
                current_year=datetime.now().year
            )
            
            subject = f"Test Completed: {test_type.replace('_', ' ').title()}"
            text_content = f"Your {test_type} test has been completed. Score: {score}/{max_score} ({percentage:.1f}%)"
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending test completed email: {e}")
            return False
    
    async def send_profile_verified_email(
        self, 
        user_email: str, 
        user_name: str, 
        verification_type: str
    ) -> bool:
        """Send profile verification email."""
        try:
            template_path = self.templates_dir / "profile_verified.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            html_content = template.format(
                user_name=user_name,
                verification_type=verification_type.replace('_', ' ').title(),
                current_year=datetime.now().year
            )
            
            subject = f"Profile Verified: {verification_type.replace('_', ' ').title()}"
            text_content = f"Your {verification_type} has been verified successfully."
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending profile verified email: {e}")
            return False
    
    async def send_password_reset_email(
        self, 
        user_email: str, 
        user_name: str, 
        reset_token: str
    ) -> bool:
        """Send password reset email."""
        try:
            template_path = self.templates_dir / "password_reset.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            reset_url = f"https://asktrabaajo.com/reset-password?token={reset_token}"
            
            html_content = template.format(
                user_name=user_name,
                reset_url=reset_url,
                current_year=datetime.now().year
            )
            
            subject = "Password Reset Request - AskTrabaajo"
            text_content = f"Click the following link to reset your password: {reset_url}"
            
            return await self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False
    
    # Email template methods
    def _get_welcome_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome to AskTrabaajo</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to AskTrabaajo!</h1>
            <p>The Future of HR Technology</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>Welcome to AskTrabaajo, the revolutionary HRTech platform that's transforming how companies hire and how people find jobs.</p>
            
            <h3>Your Role: {role}</h3>
            <p>You've registered as a <strong>{role}</strong>. Here's what you can do:</p>
            
            <ul>
                <li>Create and manage your professional profile</li>
                <li>Take AI-powered assessments</li>
                <li>Connect with employers through video interviews</li>
                <li>Track your applications and progress</li>
            </ul>
            
            <a href="https://asktrabaajo.com/dashboard" class="button">Go to Dashboard</a>
            
            <p>If you have any questions, our AI assistant is here to help 24/7!</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
            <p>This email was sent to you because you registered on AskTrabaajo.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_job_application_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Application Submitted</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .job-details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Application Submitted!</h1>
            <p>Your application has been successfully submitted</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>Great news! Your job application has been submitted successfully.</p>
            
            <div class="job-details">
                <h3>Job Details:</h3>
                <p><strong>Position:</strong> {job_title}</p>
                <p><strong>Company:</strong> {company_name}</p>
                <p><strong>Application ID:</strong> #{application_id}</p>
            </div>
            
            <h3>What happens next?</h3>
            <ul>
                <li>Your application will be reviewed by the hiring team</li>
                <li>You may be invited for an AI-powered assessment</li>
                <li>If selected, you'll be scheduled for a video interview</li>
                <li>We'll keep you updated on your application status</li>
            </ul>
            
            <a href="https://asktrabaajo.com/applications" class="button">View My Applications</a>
            
            <p>Good luck with your application!</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_interview_scheduled_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Interview Scheduled</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .interview-details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Interview Scheduled!</h1>
            <p>Your video interview has been confirmed</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>Congratulations! You've been selected for an interview.</p>
            
            <div class="interview-details">
                <h3>Interview Details:</h3>
                <p><strong>Position:</strong> {job_title}</p>
                <p><strong>Company:</strong> {company_name}</p>
                <p><strong>Date & Time:</strong> {interview_date}</p>
                <p><strong>Room ID:</strong> {room_id}</p>
            </div>
            
            <h3>How to join:</h3>
            <ul>
                <li>Click the button below 5 minutes before your scheduled time</li>
                <li>Ensure you have a stable internet connection</li>
                <li>Test your camera and microphone</li>
                <li>Find a quiet, well-lit environment</li>
            </ul>
            
            <a href="https://asktrabaajo.com/interview/{room_id}" class="button">Join Interview</a>
            
            <p>Good luck with your interview!</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_interview_reminder_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Interview Reminder</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .interview-details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #ffc107; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Interview Reminder</h1>
            <p>Your interview is coming up soon!</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>This is a friendly reminder about your upcoming interview.</p>
            
            <div class="interview-details">
                <h3>Interview Details:</h3>
                <p><strong>Position:</strong> {job_title}</p>
                <p><strong>Company:</strong> {company_name}</p>
                <p><strong>Date & Time:</strong> {interview_date}</p>
                <p><strong>Room ID:</strong> {room_id}</p>
            </div>
            
            <h3>Quick checklist:</h3>
            <ul>
                <li>✅ Test your internet connection</li>
                <li>✅ Check your camera and microphone</li>
                <li>✅ Prepare your interview space</li>
                <li>✅ Have your resume ready</li>
            </ul>
            
            <a href="https://asktrabaajo.com/interview/{room_id}" class="button">Join Interview</a>
            
            <p>Best of luck!</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_compliance_update_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Compliance Update</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .compliance-details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #17a2b8; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #17a2b8; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Compliance Update</h1>
            <p>Your compliance status has been updated</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>Your compliance information has been updated.</p>
            
            <div class="compliance-details">
                <h3>Update Details:</h3>
                <p><strong>Compliance Type:</strong> {compliance_type}</p>
                <p><strong>Status:</strong> {status}</p>
                <p><strong>Details:</strong> {details}</p>
            </div>
            
            <a href="https://asktrabaajo.com/compliance" class="button">View Compliance</a>
            
            <p>If you have any questions, please contact our support team.</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_test_completed_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Test Completed</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #6f42c1 0%, #5a2d91 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .test-details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #6f42c1; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #6f42c1; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Test Completed!</h1>
            <p>Your assessment results are ready</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>Great job! You've completed your {test_type} assessment.</p>
            
            <div class="test-details">
                <h3>Your Results:</h3>
                <p><strong>Test Type:</strong> {test_type}</p>
                <p><strong>Score:</strong> {score}/{max_score}</p>
                <p><strong>Percentage:</strong> {percentage}</p>
            </div>
            
            <a href="https://asktrabaajo.com/assessment/results" class="button">View Detailed Results</a>
            
            <p>Your results will help employers better understand your skills and qualifications.</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_profile_verified_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Profile Verified</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .verification-details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Profile Verified!</h1>
            <p>Your verification is complete</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>Congratulations! Your {verification_type} has been successfully verified.</p>
            
            <div class="verification-details">
                <h3>Verification Details:</h3>
                <p><strong>Type:</strong> {verification_type}</p>
                <p><strong>Status:</strong> ✅ Verified</p>
                <p><strong>Date:</strong> {current_year}</p>
            </div>
            
            <a href="https://asktrabaajo.com/profile" class="button">View Profile</a>
            
            <p>This verification will help increase your credibility with employers.</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_password_reset_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Password Reset</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #dc3545; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
            <p>Reset your AskTrabaajo password</p>
        </div>
        <div class="content">
            <h2>Hello {user_name}!</h2>
            <p>We received a request to reset your password for your AskTrabaajo account.</p>
            
            <div class="warning">
                <p><strong>Important:</strong> This link will expire in 1 hour for security reasons.</p>
            </div>
            
            <a href="{reset_url}" class="button">Reset Password</a>
            
            <p>If you didn't request this password reset, please ignore this email or contact our support team.</p>
            
            <p>For security, this link can only be used once.</p>
        </div>
        <div class="footer">
            <p>&copy; {current_year} AskTrabaajo. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""" 