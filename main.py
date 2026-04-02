from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, subscription, ai
from app.core.config import settings
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI SaaS Backend",
    description="Production-grade SaaS API with subscription tiers, Razorpay billing, Redis rate limiting, and LLM-powered features.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(subscription.router, prefix="/api/v1/subscription", tags=["Subscription"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Features"])


@app.get("/")
def root():
    return {
        "message": "AI SaaS Backend API",
        "plans": ["free (100 calls/month)", "pro (5000 calls/month)", "enterprise (50000 calls/month)"]
    }
