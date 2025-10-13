from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime

from api.models.database import get_db, User
from api.models.schemas import ComplianceLogCreate, ComplianceLogResponse, ComplianceVerificationRequest
from api.routes.auth import get_current_user
from api.services.compliance_service import ComplianceService

router = APIRouter()
compliance_service = ComplianceService()

@router.post("/", response_model=ComplianceLogResponse)
async def create_compliance_log(
    compliance_data: ComplianceLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new compliance log entry."""
    try:
        compliance_log = await compliance_service.create_compliance_log(
            user_id=current_user.id,
            compliance_data=compliance_data,
            db=db
        )
        
        return compliance_log
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating compliance log: {str(e)}"
        )

@router.get("/", response_model=List[ComplianceLogResponse])
async def get_user_compliance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all compliance logs for the current user."""
    try:
        compliance_logs = await compliance_service.get_user_compliance(current_user.id, db)
        return compliance_logs
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving compliance logs: {str(e)}"
        )

@router.get("/overview")
async def get_compliance_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive compliance overview for the current user."""
    try:
        overview = await compliance_service.get_compliance_overview(current_user.id, db)
        return overview
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving compliance overview: {str(e)}"
        )

@router.get("/status/{compliance_type}")
async def check_compliance_status(
    compliance_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check compliance status for a specific type."""
    try:
        status_info = await compliance_service.check_compliance_status(
            user_id=current_user.id,
            compliance_type=compliance_type,
            db=db
        )
        
        return status_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking compliance status: {str(e)}"
        )

@router.post("/verify", response_model=ComplianceLogResponse)
async def verify_compliance(
    verification_request: ComplianceVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify compliance (admin only)."""
    if current_user.role not in ["government", "consultant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only government and consultant users can verify compliance"
        )
    
    try:
        compliance_log = await compliance_service.verify_compliance(
            verification_request=verification_request,
            reviewed_by=current_user.id,
            db=db
        )
        
        return compliance_log
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error verifying compliance: {str(e)}"
        )

@router.post("/auto-verify/{compliance_type}")
async def auto_verify_compliance(
    compliance_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Automatically verify compliance based on available data."""
    try:
        verification_result = await compliance_service.auto_verify_compliance(
            user_id=current_user.id,
            compliance_type=compliance_type,
            db=db
        )
        
        return verification_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error auto-verifying compliance: {str(e)}"
        )

@router.get("/report")
async def generate_compliance_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a comprehensive compliance report."""
    try:
        report = await compliance_service.generate_compliance_report(current_user.id, db)
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating compliance report: {str(e)}"
        )

@router.get("/types/supported")
async def get_supported_compliance_types():
    """Get list of supported compliance types."""
    return {
        "compliance_types": {
            "gdpr": {
                "name": "General Data Protection Regulation",
                "description": "EU data protection regulation",
                "requirements": ["data_consent", "right_to_access", "right_to_erasure", "data_portability"],
                "expiry_days": 365
            },
            "pdpa": {
                "name": "Thailand Personal Data Protection Act",
                "description": "Thai data protection regulation",
                "requirements": ["consent_management", "data_retention", "cross_border_transfer", "breach_notification"],
                "expiry_days": 365
            },
            "security_clearance": {
                "name": "Security Clearance",
                "description": "Government security clearance",
                "requirements": ["background_check", "identity_verification", "document_verification", "facial_verification"],
                "expiry_days": 730
            },
            "international_compliance": {
                "name": "International Compliance",
                "description": "International hiring compliance",
                "requirements": ["visa_requirements", "tax_compliance", "labor_laws", "business_registration"],
                "expiry_days": 365
            }
        }
    }

@router.get("/statistics/platform")
async def get_platform_compliance_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get platform-wide compliance statistics (admin only)."""
    if current_user.role not in ["government", "consultant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only government and consultant users can view platform statistics"
        )
    
    try:
        statistics = await compliance_service.get_compliance_statistics(db)
        return statistics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving platform statistics: {str(e)}"
        )

@router.post("/gdpr/consent")
async def give_gdpr_consent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Give GDPR consent."""
    try:
        compliance_data = ComplianceLogCreate(
            compliance_type="gdpr",
            requirements={
                "data_consent": True,
                "consent_date": str(datetime.utcnow()),
                "consent_version": "1.0"
            }
        )
        
        compliance_log = await compliance_service.create_compliance_log(
            user_id=current_user.id,
            compliance_data=compliance_data,
            db=db
        )
        
        return {
            "message": "GDPR consent given successfully",
            "compliance_log_id": compliance_log.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error giving GDPR consent: {str(e)}"
        )

@router.post("/pdpa/consent")
async def give_pdpa_consent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Give Thai PDPA consent."""
    try:
        compliance_data = ComplianceLogCreate(
            compliance_type="pdpa",
            requirements={
                "consent_management": True,
                "consent_date": str(datetime.utcnow()),
                "consent_version": "1.0"
            }
        )
        
        compliance_log = await compliance_service.create_compliance_log(
            user_id=current_user.id,
            compliance_data=compliance_data,
            db=db
        )
        
        return {
            "message": "PDPA consent given successfully",
            "compliance_log_id": compliance_log.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error giving PDPA consent: {str(e)}"
        )

@router.post("/security-clearance/request")
async def request_security_clearance(
    clearance_level: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request security clearance."""
    if clearance_level not in ["Basic", "Secret", "Top Secret"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid clearance level"
        )
    
    try:
        compliance_data = ComplianceLogCreate(
            compliance_type="security_clearance",
            requirements={
                "clearance_level": clearance_level,
                "request_date": str(datetime.utcnow()),
                "status": "pending"
            }
        )
        
        compliance_log = await compliance_service.create_compliance_log(
            user_id=current_user.id,
            compliance_data=compliance_data,
            db=db
        )
        
        return {
            "message": f"Security clearance request submitted for {clearance_level} level",
            "compliance_log_id": compliance_log.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error requesting security clearance: {str(e)}"
        )

@router.post("/international/request")
async def request_international_compliance(
    country: str,
    visa_type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request international compliance verification."""
    try:
        compliance_data = ComplianceLogCreate(
            compliance_type="international_compliance",
            requirements={
                "country": country,
                "visa_type": visa_type,
                "request_date": str(datetime.utcnow()),
                "status": "pending"
            }
        )
        
        compliance_log = await compliance_service.create_compliance_log(
            user_id=current_user.id,
            compliance_data=compliance_data,
            db=db
        )
        
        return {
            "message": f"International compliance request submitted for {country}",
            "compliance_log_id": compliance_log.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error requesting international compliance: {str(e)}"
        ) 