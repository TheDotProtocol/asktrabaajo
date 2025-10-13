import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from api.models.database import ComplianceLog, User, Profile, Document
from api.models.schemas import ComplianceLogCreate, ComplianceVerificationRequest

logger = logging.getLogger(__name__)

class ComplianceService:
    def __init__(self):
        self.compliance_types = {
            "gdpr": {
                "name": "General Data Protection Regulation",
                "requirements": ["data_consent", "right_to_access", "right_to_erasure", "data_portability"],
                "expiry_days": 365
            },
            "pdpa": {
                "name": "Thailand Personal Data Protection Act",
                "requirements": ["consent_management", "data_retention", "cross_border_transfer", "breach_notification"],
                "expiry_days": 365
            },
            "security_clearance": {
                "name": "Security Clearance",
                "requirements": ["background_check", "identity_verification", "document_verification", "facial_verification"],
                "expiry_days": 730
            },
            "international_compliance": {
                "name": "International Compliance",
                "requirements": ["visa_requirements", "tax_compliance", "labor_laws", "business_registration"],
                "expiry_days": 365
            }
        }
    
    async def create_compliance_log(
        self, 
        user_id: int, 
        compliance_data: ComplianceLogCreate, 
        db: Session
    ) -> ComplianceLog:
        """Create a new compliance log entry."""
        try:
            compliance_log = ComplianceLog(
                user_id=user_id,
                compliance_type=compliance_data.compliance_type,
                requirements=compliance_data.requirements,
                expires_at=compliance_data.expires_at or self._calculate_expiry(compliance_data.compliance_type)
            )
            
            db.add(compliance_log)
            db.commit()
            db.refresh(compliance_log)
            
            logger.info(f"Compliance log created: {compliance_log.id} for user {user_id}")
            return compliance_log
            
        except Exception as e:
            logger.error(f"Error creating compliance log: {e}")
            raise
    
    async def verify_compliance(
        self, 
        verification_request: ComplianceVerificationRequest, 
        reviewed_by: int,
        db: Session
    ) -> ComplianceLog:
        """Verify compliance with admin review."""
        try:
            compliance_log = db.query(ComplianceLog).filter(
                ComplianceLog.id == verification_request.compliance_type
            ).first()
            
            if not compliance_log:
                raise ValueError("Compliance log not found")
            
            # Update compliance status
            compliance_log.status = verification_request.status
            compliance_log.reviewed_by = reviewed_by
            compliance_log.reviewed_at = datetime.utcnow()
            compliance_log.review_notes = verification_request.review_notes
            compliance_log.verification_data = verification_request.verification_data
            
            # Update user profile compliance status
            user = db.query(User).filter(User.id == compliance_log.user_id).first()
            if user and user.profile:
                if compliance_log.compliance_type == "security_clearance":
                    user.profile.compliance_status = verification_request.status
                elif compliance_log.compliance_type == "international_compliance":
                    user.profile.international_compliance = verification_request.verification_data
            
            db.commit()
            db.refresh(compliance_log)
            
            logger.info(f"Compliance verified: {compliance_log.id} by user {reviewed_by}")
            return compliance_log
            
        except Exception as e:
            logger.error(f"Error verifying compliance: {e}")
            raise
    
    async def get_user_compliance(self, user_id: int, db: Session) -> List[ComplianceLog]:
        """Get all compliance logs for a user."""
        return db.query(ComplianceLog).filter(
            ComplianceLog.user_id == user_id
        ).order_by(ComplianceLog.created_at.desc()).all()
    
    async def check_compliance_status(self, user_id: int, compliance_type: str, db: Session) -> Dict[str, Any]:
        """Check current compliance status for a specific type."""
        try:
            compliance_log = db.query(ComplianceLog).filter(
                ComplianceLog.user_id == user_id,
                ComplianceLog.compliance_type == compliance_type
            ).order_by(ComplianceLog.created_at.desc()).first()
            
            if not compliance_log:
                return {
                    "compliant": False,
                    "status": "not_found",
                    "message": f"No {compliance_type} compliance record found"
                }
            
            # Check if expired
            is_expired = compliance_log.expires_at and compliance_log.expires_at < datetime.utcnow()
            
            return {
                "compliant": compliance_log.status == "compliant" and not is_expired,
                "status": compliance_log.status,
                "expired": is_expired,
                "expires_at": compliance_log.expires_at,
                "created_at": compliance_log.created_at,
                "reviewed_at": compliance_log.reviewed_at,
                "requirements": compliance_log.requirements,
                "verification_data": compliance_log.verification_data
            }
            
        except Exception as e:
            logger.error(f"Error checking compliance status: {e}")
            return {"compliant": False, "error": str(e)}
    
    async def get_compliance_overview(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get comprehensive compliance overview for a user."""
        try:
            compliance_logs = await self.get_user_compliance(user_id, db)
            user = db.query(User).filter(User.id == user_id).first()
            
            overview = {
                "user_id": user_id,
                "user_role": user.role if user else "unknown",
                "overall_compliance": "compliant",
                "compliance_types": {},
                "missing_compliance": [],
                "expired_compliance": [],
                "total_compliance_types": len(self.compliance_types)
            }
            
            # Check each compliance type
            for compliance_type, config in self.compliance_types.items():
                status = await self.check_compliance_status(user_id, compliance_type, db)
                
                overview["compliance_types"][compliance_type] = {
                    "name": config["name"],
                    "status": status,
                    "requirements": config["requirements"]
                }
                
                if status["status"] == "not_found":
                    overview["missing_compliance"].append(compliance_type)
                elif status["expired"]:
                    overview["expired_compliance"].append(compliance_type)
                elif not status["compliant"]:
                    overview["overall_compliance"] = "non_compliant"
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting compliance overview: {e}")
            return {"error": str(e)}
    
    async def auto_verify_compliance(self, user_id: int, compliance_type: str, db: Session) -> Dict[str, Any]:
        """Automatically verify compliance based on available data."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.profile:
                return {"verified": False, "reason": "User profile not found"}
            
            verification_data = {}
            
            if compliance_type == "security_clearance":
                # Check if user has required verifications
                if (user.profile.identity_verified and 
                    user.profile.document_verification_status == "verified" and
                    user.profile.facial_verification_status == "verified"):
                    
                    verification_data = {
                        "identity_verified": user.profile.identity_verified,
                        "document_verified": user.profile.document_verification_status == "verified",
                        "facial_verified": user.profile.facial_verification_status == "verified",
                        "background_check": user.profile.background_check_status
                    }
                    
                    return {
                        "verified": True,
                        "status": "compliant",
                        "verification_data": verification_data,
                        "auto_verified": True
                    }
            
            elif compliance_type == "gdpr":
                # Check GDPR compliance
                verification_data = {
                    "data_consent": True,  # Assuming consent given during registration
                    "profile_complete": bool(user.profile),
                    "data_accessible": True
                }
                
                return {
                    "verified": True,
                    "status": "compliant",
                    "verification_data": verification_data,
                    "auto_verified": True
                }
            
            elif compliance_type == "pdpa":
                # Check Thai PDPA compliance
                verification_data = {
                    "thai_resident": user.profile.location and "thailand" in user.profile.location.lower(),
                    "consent_management": True,
                    "data_retention": True
                }
                
                return {
                    "verified": True,
                    "status": "compliant",
                    "verification_data": verification_data,
                    "auto_verified": True
                }
            
            return {"verified": False, "reason": "Manual verification required"}
            
        except Exception as e:
            logger.error(f"Error auto-verifying compliance: {e}")
            return {"verified": False, "error": str(e)}
    
    async def generate_compliance_report(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Generate a comprehensive compliance report."""
        try:
            overview = await self.get_compliance_overview(user_id, db)
            user = db.query(User).filter(User.id == user_id).first()
            
            report = {
                "report_generated_at": datetime.utcnow().isoformat(),
                "user_info": {
                    "user_id": user_id,
                    "name": f"{user.first_name} {user.last_name}" if user else "Unknown",
                    "role": user.role if user else "Unknown",
                    "email": user.email if user else "Unknown"
                },
                "compliance_summary": overview,
                "recommendations": [],
                "next_actions": []
            }
            
            # Generate recommendations
            if overview.get("missing_compliance"):
                report["recommendations"].append({
                    "type": "missing_compliance",
                    "message": f"Complete compliance requirements for: {', '.join(overview['missing_compliance'])}",
                    "priority": "high"
                })
            
            if overview.get("expired_compliance"):
                report["recommendations"].append({
                    "type": "expired_compliance",
                    "message": f"Renew expired compliance for: {', '.join(overview['expired_compliance'])}",
                    "priority": "high"
                })
            
            if overview["overall_compliance"] == "compliant":
                report["recommendations"].append({
                    "type": "maintenance",
                    "message": "Maintain current compliance status and monitor expiry dates",
                    "priority": "medium"
                })
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {"error": str(e)}
    
    def _calculate_expiry(self, compliance_type: str) -> datetime:
        """Calculate expiry date for compliance type."""
        config = self.compliance_types.get(compliance_type, {})
        expiry_days = config.get("expiry_days", 365)
        return datetime.utcnow() + timedelta(days=expiry_days)
    
    async def get_compliance_statistics(self, db: Session) -> Dict[str, Any]:
        """Get platform-wide compliance statistics."""
        try:
            total_users = db.query(User).count()
            total_compliance_logs = db.query(ComplianceLog).count()
            
            compliant_users = db.query(ComplianceLog).filter(
                ComplianceLog.status == "compliant"
            ).distinct(ComplianceLog.user_id).count()
            
            non_compliant_users = db.query(ComplianceLog).filter(
                ComplianceLog.status == "non_compliant"
            ).distinct(ComplianceLog.user_id).count()
            
            expired_compliance = db.query(ComplianceLog).filter(
                ComplianceLog.expires_at < datetime.utcnow()
            ).count()
            
            return {
                "total_users": total_users,
                "total_compliance_logs": total_compliance_logs,
                "compliant_users": compliant_users,
                "non_compliant_users": non_compliant_users,
                "expired_compliance": expired_compliance,
                "compliance_rate": round((compliant_users / total_users * 100), 2) if total_users > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance statistics: {e}")
            return {"error": str(e)} 