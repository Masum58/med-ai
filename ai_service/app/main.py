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
from app.api.chat import router as chat_router
from fastapi.openapi.utils import get_openapi



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
    app.include_router(chat_router, prefix="/ai", tags=["AI Chat"])
        # --------------------------------------------------
    # Add Swagger Bearer Auth Support
    # --------------------------------------------------
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="Med-AI Service",
            version="1.0.0",
            description="AI service for STT, TTS, OCR and Data Extraction",
            routes=app.routes,
        )

        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }

        openapi_schema["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi


    return app


# Create the FastAPI app instance
app = create_app()