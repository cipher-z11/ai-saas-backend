# fix: write README with payment flow docs
"""
AI endpoints: LLM-powered features gated by subscription tier.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import OpenAI
from app.database import get_db
from app.models.models import User, APIUsage, ChatSession, ChatMessage
from app.services.auth_service import get_current_user
from app.middleware.rate_limit import check_rate_limit
from app.core.config import settings
import json

router = APIRouter()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ChatRequest(BaseModel):
    message: str
    session_id: int = None
    stream: bool = False


class SummarizeRequest(BaseModel):
    text: str
    style: str = "concise"  # concise, detailed, bullet_points


@router.post("/chat")
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = current_user.subscription.plan.value if current_user.subscription else "free"
    check_rate_limit(current_user.id, plan)

    # Build conversation history
    history = []
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id,
        ).first()
        if session:
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.id).limit(20).all()
            history = [{"role": m.role, "content": m.content} for m in messages]

    history.append({"role": "user", "content": request.message})

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a helpful AI assistant."}] + history,
        max_tokens=800,
        temperature=0.7,
    )

    reply = response.choices[0].message.content
    tokens_used = response.usage.total_tokens

    # Save to DB
    if request.session_id:
        db.add(ChatMessage(session_id=request.session_id, role="user", content=request.message))
        db.add(ChatMessage(session_id=request.session_id, role="assistant", content=reply))

    db.add(APIUsage(
        user_id=current_user.id,
        endpoint="/ai/chat",
        tokens_used=tokens_used,
        cost_usd=tokens_used * 0.000002,
    ))
    db.commit()

    return {
        "reply": reply,
        "tokens_used": tokens_used,
        "session_id": request.session_id,
    }


@router.post("/summarize")
def summarize(
    request: SummarizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = current_user.subscription.plan.value if current_user.subscription else "free"
    check_rate_limit(current_user.id, plan)

    style_prompts = {
        "concise": "Summarize this text in 2-3 sentences.",
        "detailed": "Write a detailed summary covering all key points.",
        "bullet_points": "Summarize this text as bullet points.",
    }
    prompt = style_prompts.get(request.style, style_prompts["concise"])

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": request.text},
        ],
        max_tokens=500,
    )

    summary = response.choices[0].message.content
    tokens_used = response.usage.total_tokens

    db.add(APIUsage(user_id=current_user.id, endpoint="/ai/summarize", tokens_used=tokens_used))
    db.commit()

    return {"summary": summary, "style": request.style, "tokens_used": tokens_used}


@router.get("/sessions")
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()
    return [{"id": s.id, "name": s.session_name, "created_at": s.created_at} for s in sessions]


@router.post("/sessions")
def create_session(
    name: str = "New Chat",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = ChatSession(user_id=current_user.id, session_name=name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "name": session.session_name}
