# fix: integrate Razorpay payment gateway
"""
Rate limiting middleware based on subscription plan.
Uses Redis for distributed counter storage.
"""
import redis
from fastapi import Request, HTTPException, status
from app.core.config import settings

PLAN_LIMITS = {
    "free": 100,        # 100 API calls/month
    "pro": 5000,        # 5000 API calls/month
    "enterprise": 50000, # 50000 API calls/month
}

try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True,
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
    redis_client = None


def check_rate_limit(user_id: int, plan: str) -> dict:
    """
    Check if user has exceeded their plan's rate limit.
    Returns usage info dict.
    """
    limit = PLAN_LIMITS.get(plan, 100)
    key = f"rate_limit:user:{user_id}:month"

    if not REDIS_AVAILABLE:
        # Fallback: allow all if Redis not available
        return {"allowed": True, "used": 0, "limit": limit, "remaining": limit}

    current = redis_client.get(key)
    used = int(current) if current else 0

    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "plan": plan,
                "limit": limit,
                "used": used,
                "message": f"Upgrade to a higher plan for more API calls.",
            },
        )

    # Increment counter with 30-day TTL
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, 60 * 60 * 24 * 30)  # 30 days
    pipe.execute()

    return {"allowed": True, "used": used + 1, "limit": limit, "remaining": limit - used - 1}


def get_usage_stats(user_id: int, plan: str) -> dict:
    """Get current usage statistics for a user."""
    limit = PLAN_LIMITS.get(plan, 100)
    key = f"rate_limit:user:{user_id}:month"

    if not REDIS_AVAILABLE:
        return {"used": 0, "limit": limit, "remaining": limit, "plan": plan}

    current = redis_client.get(key)
    used = int(current) if current else 0
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "plan": plan,
        "percentage_used": round((used / limit) * 100, 2),
    }

# Final testing
