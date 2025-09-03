"""
Scanzo API - Main FastAPI Application
"""

from contextlib import asynccontextmanager
import logging
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.api.v1.endpoints import scan, health
from utils.logger import setup_logging

# Setup logging
setup_logging(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info(f"🚀 Starting {settings.app_name} v{settings.version}")
    logger.info(f"📝 Environment: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    logger.info(f"🤖 Using model: {settings.openai_model}")

    # You can add startup tasks here:
    # - Database connection
    # - Cache initialization
    # - Background task setup

    yield

    # Shutdown
    logger.info("👋 Shutting down application...")
    # Add cleanup tasks here


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Intelligent document data extraction API using Computer Vision",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with clean response"""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation Error",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    # Don't expose internal errors in production
    if settings.debug:
        error_message = str(exc)
    else:
        error_message = "An internal error occurred"

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": error_message
        }
    )


# Include routers
app.include_router(
    health.router,
    prefix="/api",
    tags=["health"]
)

app.include_router(
    scan.router,
    prefix="/api/v1",
    tags=["scan"]
)


# Root endpoint
@app.get("/", response_model=Dict[str, str])
async def root():
    """API root endpoint with basic information"""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )