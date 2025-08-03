# main.py - ChainWatch Backend Entry Point
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn

from app.core.database import init_db, get_db
from app.core.scheduler import AgentScheduler
from app.api.endpoints import agents, alerts, health
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global scheduler
    
    # Startup
    logger.info("🚀 Starting ChainWatch Backend...")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Start scheduler
    scheduler = AgentScheduler()
    await scheduler.start()
    logger.info("✅ Agent scheduler started")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down ChainWatch Backend...")
    if scheduler:
        await scheduler.stop()
    logger.info("✅ Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="ChainWatch API",
    description="AI-powered blockchain monitoring agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1/agents")
app.include_router(alerts.router, prefix="/api/v1/alerts")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ChainWatch API",
        "version": "1.0.0",
        "status": "operational"
    }

# Dependency to get scheduler
def get_scheduler():
    global scheduler
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    return scheduler

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )