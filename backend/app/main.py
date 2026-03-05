"""FastAPI application entry point — v2 with multi-agent pipeline."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, doctors, generate, notes, reports
from app.services.ai_search import ai_search_service
from app.services.blob_storage import blob_service
from app.services.cosmos_db import cosmos_service
from app.services.openai_service import openai_service
from app.utils.telemetry import setup_telemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize Azure service clients and telemetry on startup."""
    logger.info("Initializing services for multi-agent pipeline...")
    try:
        await cosmos_service.initialize()
        await blob_service.initialize()
        await openai_service.initialize()
        await ai_search_service.initialize()
        logger.info("All Azure services initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Azure services: %s", e)
        logger.warning("Application starting with degraded service connectivity")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="Impressions Generator v2",
    description=(
        "Healthcare radiology/oncology clinical note generation API "
        "powered by a multi-agent pipeline (MAF)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# OpenTelemetry instrumentation
setup_telemetry(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(doctors.router)
app.include_router(notes.router)
app.include_router(generate.router)
app.include_router(reports.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0", "pipeline": "multi-agent"}
