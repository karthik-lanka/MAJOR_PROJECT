"""
FastAPI application entry point.
AI-Powered Multimodal Study Assistant Using RAG and LLMs.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, documents, chat, study
from app.core.config import get_settings
from app.core.database import init_database, close_database
from app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting AI-Powered Multimodal Study Assistant backend...")

    # Initialize SQLite database schema
    await init_database(settings.database_url)
    logger.info(f"Database initialized: {settings.database_url}")

    yield

    # Clean shutdown
    logger.info("Shutting down application...")
    await close_database()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="AI-Powered Multimodal Study Assistant",
    description="RAG and LLM-powered academic study assistant with claim verification, citations, and adaptive responses.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
settings = get_settings()
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.frontend_url and settings.frontend_url not in allowed_origins:
    allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(study.router)


@app.get("/")
async def root():
    """Root endpoint for status check and quick API navigation."""
    return {
        "name": "AI-Powered Multimodal Study Assistant API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api_status": "/api/status",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global fallback exception handler."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "error_type": type(exc).__name__,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
