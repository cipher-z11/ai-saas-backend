"""
Subscription management routes with Razorpay payment integration.
"""
import razorpay
import hmac
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.database import get_db
from app.models.models import User, Subscription, PlanEnum, SubscriptionStatusEnum
from app.services.auth_service import get_current_user
from app.middleware.rate_limit import get_usage_stats
from app.core.config import settings

router = APIRouter()

PLAN_PRICES = {
    "pro": 99900,        # ₹999/month in paise
    "enterprise": 299900, # ₹2999/month in paise
}

PLAN_LIMITS = {"free": 100, "pro": 5000, "enterprise": 50000}


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class UpgradeRequest(BaseModel):
    plan: str  # "pro" or "enterprise"


@router.get("/current")
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = current_user.subscription
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found")

    plan_name = sub.plan.value
    usage = get_usage_stats(current_user.id, plan_name)

    return {
        "plan": plan_name,
        "status": sub.status.value,
        "api_calls_used": usage["used"],
        "api_calls_limit": usage["limit"],
        "api_calls_remaining": usage["remaining"],
        "percentage_used": usage["percentage_used"],
        "period_end": sub.current_period_end,
    }


@router.post("/create-order")
def create_payment_order(
    request: UpgradeRequest,
    current_user: User = Depends(get_current_user),
):
    if request.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {list(PLAN_PRICES.keys())}")

    amount = PLAN_PRICES[request.plan]
    client = get_razorpay_client()

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": f"sub_{current_user.id}_{request.plan}",
        "notes": {
            "user_id": str(current_user.id),
            "plan": request.plan,
            "email": current_user.email,
        }
    })

    return {
        "order_id": order["id"],
        "amount": amount,
        "currency": "INR",
        "plan": request.plan,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
    }


@router.post("/verify-payment")
def verify_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    plan: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify Razorpay payment signature and activate subscription."""
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if expected_signature != razorpay_signature:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Activate subscription
    sub = current_user.subscription
    sub.plan = PlanEnum(plan)
    sub.status = SubscriptionStatusEnum.active
    sub.razorpay_subscription_id = razorpay_payment_id
    sub.api_calls_limit = PLAN_LIMITS.get(plan, 100)
    sub.current_period_start = datetime.utcnow()
    sub.current_period_end = datetime.utcnow() + timedelta(days=30)
    db.commit()

    return {
        "message": f"Subscription upgraded to {plan} successfully!",
        "plan": plan,
        "valid_until": sub.current_period_end,
    }


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = current_user.subscription
    sub.status = SubscriptionStatusEnum.cancelled
    db.commit()
    return {"message": "Subscription cancelled. You can still use the service until the period ends."}
