from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from api.models.database import get_db, User, Payment, Interview, AuditLog
from api.models.schemas import PaymentCreate, PaymentResponse
from api.routes.auth import get_current_user

router = APIRouter()

# Crypto wallet addresses (you'll need to provide these)
CRYPTO_WALLETS = {
    "3DOT": "your-3dot-wallet-address",
    "ASK": "your-ask-wallet-address", 
    "ARHC": "your-arhc-wallet-address",
    "USDT": "your-usdt-wallet-address",
    "BTC": "your-btc-wallet-address",
    "BNB": "your-bnb-wallet-address"
}

@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new payment"""
    
    # Generate transaction ID
    transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        interview_id=payment_data.interview_id,
        amount=payment_data.amount,
        currency=payment_data.currency,
        payment_method=payment_data.payment_method,
        crypto_type=payment_data.crypto_type,
        transaction_id=transaction_id,
        status="pending"
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="payment_created",
        resource="payments",
        details={
            "amount": payment_data.amount,
            "currency": payment_data.currency,
            "payment_method": payment_data.payment_method,
            "transaction_id": transaction_id
        }
    )
    db.add(audit_log)
    db.commit()
    
    return payment

@router.get("/crypto-wallets")
async def get_crypto_wallets():
    """Get crypto wallet addresses for payment"""
    return {
        "wallets": CRYPTO_WALLETS,
        "supported_currencies": list(CRYPTO_WALLETS.keys()),
        "exchange_rate_note": "Rates are updated in real-time"
    }

@router.post("/{payment_id}/confirm")
async def confirm_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm a payment (for crypto payments)"""
    
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Payment is not pending")
    
    # Update payment status (in real implementation, you'd verify the payment)
    payment.status = "completed"
    db.commit()
    
    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="payment_confirmed",
        resource="payments",
        details={"payment_id": payment_id, "transaction_id": payment.transaction_id}
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Payment confirmed", "transaction_id": payment.transaction_id}

@router.get("/", response_model=List[PaymentResponse])
async def get_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's payment history"""
    payments = db.query(Payment).filter(Payment.user_id == current_user.id).all()
    return payments

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific payment details"""
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment

@router.post("/calculate-interview-cost")
async def calculate_interview_cost(
    duration_minutes: int,
    currency: str = "USD"
):
    """Calculate cost for video interview ($1/minute)"""
    cost_per_minute = 1.0  # USD
    
    # Convert to other currencies if needed
    if currency != "USD":
        # In real implementation, you'd use a currency conversion API
        exchange_rates = {
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 110.0
        }
        cost_per_minute = cost_per_minute * exchange_rates.get(currency, 1.0)
    
    total_cost = duration_minutes * cost_per_minute
    
    return {
        "duration_minutes": duration_minutes,
        "cost_per_minute": cost_per_minute,
        "total_cost": total_cost,
        "currency": currency
    } 