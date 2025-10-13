import os
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import base64
from pathlib import Path
import logging
from sqlalchemy.orm import Session

from api.models.database import Document, User, ComplianceLog
from api.models.schemas import DocumentCreate, DocumentVerificationRequest

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.upload_dir = Path("uploads/documents")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    async def upload_document(
        self, 
        user_id: int, 
        file_data: bytes, 
        file_name: str, 
        document_type: str,
        db: Session
    ) -> Document:
        """Upload and process a document with security features."""
        try:
            # Validate file
            if not self._validate_file(file_name, len(file_data)):
                raise ValueError("Invalid file format or size")
            
            # Generate unique file path
            file_extension = Path(file_name).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = self.upload_dir / unique_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Generate security hashes
            encryption_hash = self._generate_encryption_hash(file_data)
            blockchain_hash = self._generate_blockchain_hash(file_data, user_id, document_type)
            
            # Create document record
            document = Document(
                user_id=user_id,
                document_type=document_type,
                file_name=file_name,
                file_path=str(file_path),
                file_size=len(file_data),
                mime_type=self._get_mime_type(file_extension),
                encryption_hash=encryption_hash,
                blockchain_hash=blockchain_hash,
                expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year expiry
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"Document uploaded successfully: {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            raise
    
    async def verify_document(
        self, 
        verification_request: DocumentVerificationRequest, 
        verified_by: int,
        db: Session
    ) -> Document:
        """Verify a document with admin approval."""
        try:
            document = db.query(Document).filter(Document.id == verification_request.document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            # Update verification status
            document.verification_status = verification_request.status
            document.verified_by = verified_by
            document.verified_at = datetime.utcnow()
            document.verification_notes = verification_request.verification_notes
            
            # Update user profile verification status
            user = db.query(User).filter(User.id == document.user_id).first()
            if user and user.profile:
                if verification_request.status == "verified":
                    user.profile.document_verification_status = "verified"
                elif verification_request.status == "rejected":
                    user.profile.document_verification_status = "rejected"
            
            db.commit()
            db.refresh(document)
            
            logger.info(f"Document verified: {document.id} by user {verified_by}")
            return document
            
        except Exception as e:
            logger.error(f"Error verifying document: {e}")
            raise
    
    async def get_user_documents(self, user_id: int, db: Session) -> List[Document]:
        """Get all documents for a user."""
        return db.query(Document).filter(
            Document.user_id == user_id,
            Document.is_active == True
        ).order_by(Document.uploaded_at.desc()).all()
    
    async def get_document_by_id(self, document_id: int, user_id: int, db: Session) -> Optional[Document]:
        """Get a specific document with access control."""
        return db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id,
            Document.is_active == True
        ).first()
    
    async def delete_document(self, document_id: int, user_id: int, db: Session) -> bool:
        """Soft delete a document."""
        try:
            document = db.query(Document).filter(
                Document.id == document_id,
                Document.user_id == user_id
            ).first()
            
            if not document:
                return False
            
            # Soft delete
            document.is_active = False
            db.commit()
            
            logger.info(f"Document deleted: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    async def get_document_file(self, document_id: int, user_id: int, db: Session) -> Optional[bytes]:
        """Get document file content with access control."""
        try:
            document = await self.get_document_by_id(document_id, user_id, db)
            if not document:
                return None
            
            # Check if file exists
            file_path = Path(document.file_path)
            if not file_path.exists():
                logger.error(f"Document file not found: {document.file_path}")
                return None
            
            # Read file
            with open(file_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Error reading document file: {e}")
            return None
    
    def _validate_file(self, file_name: str, file_size: int) -> bool:
        """Validate file format and size."""
        file_extension = Path(file_name).suffix.lower()
        
        if file_extension not in self.allowed_extensions:
            return False
        
        if file_size > self.max_file_size:
            return False
        
        return True
    
    def _generate_encryption_hash(self, file_data: bytes) -> str:
        """Generate encryption hash for file integrity."""
        return hashlib.sha256(file_data).hexdigest()
    
    def _generate_blockchain_hash(self, file_data: bytes, user_id: int, document_type: str) -> str:
        """Generate blockchain hash for immutable verification."""
        content = f"{user_id}:{document_type}:{self._generate_encryption_hash(file_data)}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_mime_type(self, file_extension: str) -> str:
        """Get MIME type for file extension."""
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        return mime_types.get(file_extension.lower(), 'application/octet-stream')
    
    async def check_document_integrity(self, document_id: int, db: Session) -> Dict[str, Any]:
        """Check document integrity using stored hashes."""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {"valid": False, "error": "Document not found"}
            
            # Read current file
            file_path = Path(document.file_path)
            if not file_path.exists():
                return {"valid": False, "error": "File not found"}
            
            with open(file_path, 'rb') as f:
                current_data = f.read()
            
            # Check encryption hash
            current_hash = self._generate_encryption_hash(current_data)
            hash_valid = current_hash == document.encryption_hash
            
            return {
                "valid": hash_valid,
                "document_id": document_id,
                "hash_valid": hash_valid,
                "file_size": len(current_data),
                "stored_size": document.file_size,
                "size_match": len(current_data) == document.file_size
            }
            
        except Exception as e:
            logger.error(f"Error checking document integrity: {e}")
            return {"valid": False, "error": str(e)}
    
    async def get_document_statistics(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get document statistics for a user."""
        documents = await self.get_user_documents(user_id, db)
        
        total_documents = len(documents)
        verified_documents = len([d for d in documents if d.verification_status == "verified"])
        pending_documents = len([d for d in documents if d.verification_status == "pending"])
        rejected_documents = len([d for d in documents if d.verification_status == "rejected"])
        
        total_size = sum(d.file_size for d in documents)
        
        return {
            "total_documents": total_documents,
            "verified_documents": verified_documents,
            "pending_documents": pending_documents,
            "rejected_documents": rejected_documents,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        } 