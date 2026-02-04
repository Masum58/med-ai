"""
ocr.py (Schemas)

This file defines the data structure (schemas) used for OCR-related APIs.

Purpose of this file:
- Clearly define what data the OCR API will return
- Help FastAPI generate clean and user-friendly API documentation
- Validate response data automatically

This file does NOT:
- Perform OCR
- Handle file uploads
- Call any services
"""

from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    """
    OCRResponse

    This schema represents the response returned after
    successfully extracting text from a document.

    It contains only raw extracted text.
    """

    raw_text: str = Field(
        ...,
        description=(
            "The full text extracted from the uploaded document. "
            "This text comes directly from OCR or document parsing "
            "and has not been modified or interpreted."
        ),
        example="Paracetamol 500mg twice daily after food"
    )
