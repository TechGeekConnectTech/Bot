from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
from app.core.config import settings
from app.core.logging_config import setup_logging
import logging
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.knowledge import router as knowledge_router
from app.core.database import engine, Base

# Setup logging system
setup_logging()
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

app = FastAPI(
    title="DC AutoAssist API",
    description="API Support Automation Chatbot for HSBC DC Team",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

logger.info("HSBC AutoAssist API initialized")

# Configure CORS - Allow server IP and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://77.37.45.138:3000",
        "http://77.37.45.138:8000",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat & Incidents"])  # Includes both chat and incident routes
app.include_router(admin_router, prefix="/api/admin", tags=["Administration"])
app.include_router(knowledge_router, tags=["Knowledge Management"])

@app.on_event("startup")
async def startup_event():
    logger.info("HSBC AutoAssist API starting up...")
    logger.info(f"CORS origins configured: {[origin for origin in app.user_middleware if hasattr(origin, 'allow_origins')]}")
    logger.info("API is ready to serve requests")

@app.get("/")
async def root():
    return {
        "message": "Welcome to HSBC AutoAssist API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "HSBC AutoAssist"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )