from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from api.models.database import get_db, User, Payment, Interview
from api.models.schemas import PaymentCreate, PaymentResponse
from api.routes.auth import get_current_user

router = APIRouter()

# Crypto wallet addresses (in production, these would be stored securely)
CRYPTO_WALLETS = {
    "3dot": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "ask": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
    "arhc": "0x1234567890123456789012345678901234567890",
    "usdt": "TQn9Y2khDD95J42FQtQTdwVVRKjqEQJfHr",
    "btc": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "bnb": "bnb1jxfh2g85q3v0tdq56fnevx6xcxtcnhtsmcu64m"
}

@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new payment."""
    # Validate payment method
    valid_methods = ["stripe", "crypto_3dot", "crypto_ask", "crypto_arhc", "crypto_usdt", "crypto_btc", "crypto_bnb"]
    if payment_data.payment_method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method"
        )
    
    # If payment is for an interview, validate it exists
    if payment_data.interview_id:
        interview = db.query(Interview).filter(Interview.id == payment_data.interview_id).first()
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
    
    # Create payment record
    db_payment = Payment(
        user_id=current_user.id,
        interview_id=payment_data.interview_id,
        amount=payment_data.amount,
        currency=payment_data.currency,
        payment_method=payment_data.payment_method,
        status="pending"
    )
    
    # Add crypto wallet address if it's a crypto payment
    if payment_data.payment_method.startswith("crypto_"):
        crypto_type = payment_data.payment_method.replace("crypto_", "")
        db_payment.crypto_wallet_address = CRYPTO_WALLETS.get(crypto_type)
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    return db_payment

@router.get("/crypto-wallets")
async def get_crypto_wallets():
    """Get crypto wallet addresses for payments."""
    return {
        "wallets": CRYPTO_WALLETS,
        "supported_currencies": list(CRYPTO_WALLETS.keys())
    }

@router.post("/{payment_id}/confirm")
async def confirm_payment(
    payment_id: int,
    transaction_hash: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm a crypto payment."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to confirm this payment"
        )
    
    if not payment.payment_method.startswith("crypto_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only crypto payments can be confirmed manually"
        )
    
    if transaction_hash:
        payment.crypto_transaction_hash = transaction_hash
    
    payment.status = "processing"
    db.commit()
    
    return {"message": "Payment confirmation submitted", "payment_id": payment_id}

@router.get("/", response_model=List[PaymentResponse])
async def get_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's payment history."""
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).all()
    
    return payments

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific payment details."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )
    
    return payment

@router.get("/interview/{interview_id}/cost")
async def calculate_interview_cost(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate the cost for an interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.participant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this interview cost"
        )
    
    return {
        "interview_id": interview_id,
        "duration_minutes": interview.duration_minutes,
        "cost_per_minute": interview.cost_per_minute,
        "total_cost": interview.total_cost,
        "currency": "USD"
    } 