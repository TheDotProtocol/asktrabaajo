from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import base64

from api.models.database import get_db, User
from api.models.schemas import DocumentResponse, DocumentVerificationRequest
from api.routes.auth import get_current_user
from api.services.document_service import DocumentService

router = APIRouter()
document_service = DocumentService()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document with security features."""
    try:
        # Read file data
        file_data = await file.read()
        
        # Upload document
        document = await document_service.upload_document(
            user_id=current_user.id,
            file_data=file_data,
            file_name=file.filename,
            document_type=document_type,
            db=db
        )
        
        return document
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error uploading document: {str(e)}"
        )

@router.get("/", response_model=List[DocumentResponse])
async def get_user_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for the current user."""
    try:
        documents = await document_service.get_user_documents(current_user.id, db)
        return documents
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving documents: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document."""
    try:
        document = await document_service.get_document_by_id(document_id, current_user.id, db)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document: {str(e)}"
        )

@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a document file."""
    try:
        file_data = await document_service.get_document_file(document_id, current_user.id, db)
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
        
        document = await document_service.get_document_by_id(document_id, current_user.id, db)
        
        return {
            "file_data": base64.b64encode(file_data).decode(),
            "file_name": document.file_name,
            "mime_type": document.mime_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading document: {str(e)}"
        )

@router.post("/{document_id}/verify", response_model=DocumentResponse)
async def verify_document(
    document_id: int,
    verification_request: DocumentVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify a document (admin only)."""
    if current_user.role not in ["government", "consultant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only government and consultant users can verify documents"
        )
    
    try:
        document = await document_service.verify_document(
            verification_request=verification_request,
            verified_by=current_user.id,
            db=db
        )
        
        return document
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error verifying document: {str(e)}"
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document (soft delete)."""
    try:
        success = await document_service.delete_document(document_id, current_user.id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )

@router.get("/{document_id}/integrity")
async def check_document_integrity(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check document integrity using stored hashes."""
    try:
        integrity_check = await document_service.check_document_integrity(document_id, db)
        return integrity_check
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking document integrity: {str(e)}"
        )

@router.get("/statistics/overview")
async def get_document_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document statistics for the current user."""
    try:
        statistics = await document_service.get_document_statistics(current_user.id, db)
        return statistics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document statistics: {str(e)}"
        )

@router.get("/types/supported")
async def get_supported_document_types():
    """Get list of supported document types."""
    return {
        "document_types": [
            "passport",
            "national_id",
            "drivers_license",
            "birth_certificate",
            "educational_certificate",
            "professional_certification",
            "employment_contract",
            "business_license",
            "tax_document",
            "visa_document",
            "security_clearance",
            "background_check",
            "medical_certificate",
            "insurance_document",
            "other"
        ],
        "max_file_size_mb": 10,
        "supported_formats": ["pdf", "jpg", "jpeg", "png", "doc", "docx"]
    } 