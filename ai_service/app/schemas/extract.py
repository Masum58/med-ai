"""
extract.py (schemas)

Pydantic models for extraction API endpoints.

UPDATED: Now accepts both raw_text and STT response format.

These schemas define:
- Request format for extraction endpoints
- Response format with structured data
- Validation rules
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Any, Optional


class ExtractionRequest(BaseModel):
    """
    Request schema for extraction endpoints.
    
    UPDATED: Accepts both formats:
    1. Direct text: {"raw_text": "..."}
    2. STT output: {"text": "...", "language": "..."}
    
    Used by:
    - POST /extract/prescription
    - POST /extract/voice-intent
    - POST /extract/lab-report
    """
    raw_text: Optional[str] = Field(
        default=None,
        description="Unstructured text from OCR",
        examples=["Name: John Doe\nAge: 45\nTab. Paracetamol 500mg BD"]
    )
    
    # STT format fields
    text: Optional[str] = Field(
        default=None,
        description="Text from STT service",
        examples=["I want to know today's medicine"]
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Language from STT (optional)",
        examples=["en"]
    )
    
    @model_validator(mode='after')
    def validate_text_present(self):
        """
        Ensure either raw_text or text is provided.
        
        What happens here:
        1. Check if raw_text exists
        2. If not, check if text exists
        3. Use text as raw_text if present
        4. Raise error if both missing
        
        This allows both formats:
        - {"raw_text": "..."}
        - {"text": "...", "language": "..."}
        """
        # If raw_text not provided but text is provided
        if not self.raw_text and self.text:
            # Auto-convert text to raw_text
            self.raw_text = self.text
        
        # If neither provided, raise error
        if not self.raw_text:
            raise ValueError("Either 'raw_text' or 'text' field is required")
        
        return self
    
    class Config:
        # Allow extra fields (like language) without error
        extra = "allow"


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