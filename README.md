# 💡 AI SaaS Backend with Subscription Management

A production-grade SaaS API backend featuring plan-based access control, Razorpay subscription billing, Redis-powered rate limiting, and LLM-powered AI features.

## Features

- 🔐 JWT Authentication (register/login/me)
- 💳 Razorpay Payment Integration (create order → verify payment → activate plan)
- 🚦 Redis Rate Limiting per subscription tier
- 🤖 LLM-powered Chat & Summarization APIs
- 📊 API usage tracking (tokens used, cost estimation)
- 🏗️ Clean architecture: routes → services → models

## Subscription Plans

| Plan | Price | API Calls/Month |
|---|---|---|
| Free | ₹0 | 100 |
| Pro | ₹999 | 5,000 |
| Enterprise | ₹2,999 | 50,000 |

## Tech Stack

- **FastAPI** — REST API framework
- **PostgreSQL + SQLAlchemy** — Database & ORM
- **Redis** — Rate limiting counters
- **Razorpay** — Payment gateway
- **OpenAI GPT** — LLM features
- **JWT (python-jose)** — Authentication

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in DB, OpenAI, Razorpay, Redis credentials
uvicorn main:app --reload
```

## API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Create account | No |
| POST | `/api/v1/auth/login` | Login, get token | No |
| GET | `/api/v1/auth/me` | Get current user | Yes |
| GET | `/api/v1/subscription/current` | View plan & usage | Yes |
| POST | `/api/v1/subscription/create-order` | Create Razorpay order | Yes |
| POST | `/api/v1/subscription/verify-payment` | Activate plan | Yes |
| POST | `/api/v1/subscription/cancel` | Cancel subscription | Yes |
| POST | `/api/v1/ai/chat` | LLM chat | Yes |
| POST | `/api/v1/ai/summarize` | Text summarization | Yes |
| GET | `/api/v1/ai/sessions` | List chat sessions | Yes |
| POST | `/api/v1/ai/sessions` | Create chat session | Yes |

## Payment Flow

```
1. POST /subscription/create-order  → get order_id
2. Open Razorpay checkout in frontend
3. POST /subscription/verify-payment → subscription activated
```
