from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..oauth2 import get_current_user
from ..mockGateway import MockRazorpayClient
import os

router = APIRouter(prefix="/payments", tags=["Payments"])


# Initialize our Fake Bank
# You can put ANYTHING here,
KEY_ID = os.getenv("KEY_ID", "1234") 
KEY_SECRET = os.getenv("KEY_SECRET", "5678")

client = MockRazorpayClient(auth=(KEY_ID,KEY_SECRET)) #an object is created


# --- ACT 1: CREATE ORDER (Server-Side) ---
@router.post("/create-order",response_model=schemas.OrderResponse)
def create_order(request : schemas.OrderCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    amount_inr = request.amount
    amount_paise = 100 * amount_inr
    
    data = {
        "amount" : amount_paise,
        "currency" : "INR",
        "payment_capture" : 1
    }
    
    # Now crreate a razorpay order
    try:
        razorpay_order = client.order.create(data=data)
    except Exception as e: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Error connecting to Payment Gateway")
    
    
    # Create an entry in the database (STATUS : CREATED)
    new_transaction = models.Transactions(
        user_id = current_user.id,
        gateway_order_id = razorpay_order['id'],
        amount = amount_paise,
        status = "CREATED"
    )
    
    db.add(new_transaction)
    db.commit()
    
    return {
        "id" : razorpay_order['id'],
        "amount" : razorpay_order['amount'],
        "currency" : razorpay_order['currency']
    }
    
    
@router.post("/verify-payment", status_code=status.HTTP_200_OK, response_model=schemas.PaymentVerificationResponse)
def verify_payment(
    request: schemas.PaymentVerification, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    params = {
        "razorpay_order_id": request.gateway_order_id,
        "razorpay_payment_id": request.gateway_payment_id,
        "razorpay_signature": request.gateway_signature
    }

    # 1. Verify Signature (Check this FIRST, outside the general try block if possible, or catch specific errors)
    try:
        if not client.utility_verify_payment_signature(params=params):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Payment Signature")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Payment Signature")

    # 2. Find Transaction
    transaction = db.query(models.Transactions).filter(
        models.Transactions.gateway_order_id == request.gateway_order_id
    ).first()
    
    if not transaction:
        # This will now safely return 404 instead of crashing
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # 3. Update Database (Wrap ONLY the DB part in a try/except for safety)
    try:
        transaction.gateway_payment_id = request.gateway_payment_id # type: ignore
        transaction.gateway_signature = request.gateway_signature # type: ignore
        transaction.status = "SUCCESS" # type: ignore
        
        db.commit()
        
    except Exception as e:
        db.rollback() # Good practice to rollback if commit fails
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database Commit Failed")

    return {
        "status": "SUCCESS",
        "message": "Payment verified successfully"
    }