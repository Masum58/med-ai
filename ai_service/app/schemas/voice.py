"""
voice.py (schemas)

This file contains all Pydantic models related to
voice processing such as Speech-to-Text (STT)
and Text-to-Speech (TTS).

These schemas define:
- What data the API expects
- What data the API returns
- Validation rules
- API documentation details
"""

from pydantic import BaseModel, Field
from typing import Optional


class STTResponse(BaseModel):
    """
    Response model for Speech-to-Text.

    This is returned after converting an audio file
    into readable text.
    
    Used by:
    - POST /voice/stt endpoint
    """
    text: str = Field(
        ...,
        description="Extracted text from the uploaded audio file",
        example="I need to add Paracetamol 500mg twice daily"
    )
    language: str = Field(
        ...,
        description="Detected language of the audio content",
        example="en"
    )


class TTSRequest(BaseModel):
    """
    Request model for Text-to-Speech.

    This is sent by the client when they want
    to convert text into audio.
    
    Used by:
    - POST /voice/tts endpoint
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Text that will be converted into speech",
        example="Time to take your Paracetamol 500mg"
    )
    
    voice: Optional[str] = Field(
        default="nova",
        description=(
            "Voice type to be used for speech generation. "
            "Options: alloy, echo, fable, onyx, nova, shimmer. "
            "Default is 'nova' (clear female voice, good for elderly users)"
        ),
        example="nova"
    )
    
    speed: Optional[float] = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description=(
            "Speed of speech. "
            "Range: 0.25 (very slow) to 4.0 (very fast). "
            "Default is 1.0 (normal speed). "
            "Use 0.9 for elderly users (slightly slower, clearer)"
        ),
        example=0.9
    )