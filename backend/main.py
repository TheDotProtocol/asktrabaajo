from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from api.models.simple_database import create_tables
from api.routes import auth, users, jobs, tests, interviews, payments, ai_assistant, documents, compliance, currencies, notifications, realtime, advanced_ai, analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting AskTrabaajo Backend...")
    create_tables()
    print("✅ Database tables created/verified")
    print("✅ Backend ready to serve requests")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down AskTrabaajo Backend...")

app = FastAPI(
    title="AskTrabaajo API",
    description="A disruptive HRTech platform that replaces traditional resumes and job portals with a structured, real-time, AI-based recruitment engine.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(tests.router, prefix="/api/tests", tags=["Assessments"])
app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(ai_assistant.router, prefix="/api/ai", tags=["AI Assistant"])

# Government & Foreign Company Features
app.include_router(documents.router, prefix="/api/documents", tags=["Document Management"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["Compliance"])
app.include_router(currencies.router, prefix="/api/currencies", tags=["Multi-Currency"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["Real-time"])

# Phase 3: Advanced Features
app.include_router(advanced_ai.router, prefix="/api/advanced-ai", tags=["Advanced AI"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to AskTrabaajo API",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "AI-powered assessments",
            "Video interviews with facial analysis",
            "Government & foreign company compliance",
            "Multi-currency support",
            "Document management & verification",
            "Blockchain-secured data"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AskTrabaajo Backend"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 