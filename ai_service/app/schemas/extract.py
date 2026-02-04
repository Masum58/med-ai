"""
extract.py (schemas)

Pydantic models for extraction API endpoints.

These schemas define:
- Request format for extraction endpoints
- Response format with structured data
- Validation rules
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class ExtractionRequest(BaseModel):
    """
    Request schema for extraction endpoints.
    
    Used by:
    - POST /extract/prescription
    - POST /extract/voice-intent
    - POST /extract/lab-report
    """
    raw_text: str = Field(
        ...,
        description="Unstructured text from OCR or voice",
        example="Name: John Doe\nAge: 45\nTab. Paracetamol 500mg BD"
    )


class ExtractionResponse(BaseModel):
    """
    Response schema for extraction endpoints.
    
    Contains extracted structured data.
    """
    success: bool = Field(
        ..., 
        description="Whether extraction succeeded"
    )
    
    data: Dict[str, Any] = Field(
        ..., 
        description="Extracted structured data"
    )
    
    message: str = Field(
        default="", 
        description="Optional message about extraction"
    )