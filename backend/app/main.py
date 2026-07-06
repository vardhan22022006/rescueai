from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from contextlib import asynccontextmanager

from app.scheduler import start_scheduler, shutdown_scheduler, get_scheduler_status
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup: Start the background scheduler
    start_scheduler()
    
    yield
    
    # Shutdown: Stop the background scheduler
    shutdown_scheduler()


app = FastAPI(
    title="RescueAI API",
    description="Disaster Response Management System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RescueAI API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "api_prefix": "/api"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    scheduler_status = get_scheduler_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "rescueai-api",
        "scheduler": scheduler_status
    }
