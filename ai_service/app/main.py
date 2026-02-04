"""
main.py

This is the main entry point of the FastAPI application.
Here we create the FastAPI app and register all API routes.

This file does NOT contain business logic.
It only wires everything together.
"""

from fastapi import FastAPI

# Import API routers
from app.api.voice import router as voice_router
from app.api.ocr import router as ocr_router
from app.api.health import router as health_router
from app.api.extract import router as extract_router


def create_app() -> FastAPI:
    """
    Creates and returns the FastAPI application instance.
    This function helps keep the app creation clean and testable.
    """
    app = FastAPI(
        title="Med-AI Service",
        description="AI service for STT, TTS, OCR and Data Extraction",
        version="1.0.0"
    )

    # Register API routes
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(voice_router, prefix="/voice", tags=["Voice"])
    app.include_router(ocr_router, prefix="/ocr", tags=["OCR"])
    app.include_router(extract_router, prefix="/extract", tags=["Extract"])

    return app


# Create the FastAPI app instance
app = create_app()