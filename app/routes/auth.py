from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.models import User, Subscription, PlanEnum
from app.services.auth_service import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    plan: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=request.name,
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    db.flush()

    # Create free-tier subscription automatically
    subscription = Subscription(
        user_id=user.id,
        plan=PlanEnum.free,
        api_calls_limit=100,
    )
    db.add(subscription)
    db.commit()
    db.refresh(user)

    return {"message": "Account created successfully", "user_id": user.id, "plan": "free"}


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id)})
    plan = user.subscription.plan.value if user.subscription else "free"

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        plan=plan,
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "plan": current_user.subscription.plan.value if current_user.subscription else "free",
    }

# Integrate Razorpay payment gateway

# Fix rate limit edge cases
