"""
voice.py (API - Updated with TTS)

This file defines all voice-related API endpoints.

Current endpoints:
- POST /voice/stt - Speech to Text
- POST /voice/tts - Text to Speech

This file does NOT:
- Talk to the database
- Make business decisions
- Store any data
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import Response

from app.schemas.voice import STTResponse, TTSRequest
from app.services.stt import SpeechToTextService
from app.services.tts import TextToSpeechService
from app.config import OPENAI_API_KEY

# Create a router object for all voice-related endpoints
router = APIRouter()


@router.post(
    "/stt",
    response_model=STTResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert speech to text",
    description="Upload an audio file and convert spoken content into text."
)
async def speech_to_text(file: UploadFile = File(...)):
    """
    Speech-to-Text endpoint.

    Steps performed here:
    1. Validate the uploaded audio file
    2. Read audio bytes into memory
    3. Call the STT service to extract text
    4. Return the extracted text and detected language

    Parameters:
    - file: Audio file uploaded by the user

    Returns:
    - STTResponse containing extracted text and language
    
    Called by:
    - Mobile app (voice input feature)
    - Frontend web app
    """

    # Step 1: Validate that a file name exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is required"
        )

    # Step 2: Read the audio file into memory
    audio_bytes = await file.read()

    # Step 3: Ensure the uploaded file is not empty
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty"
        )

    # Step 4: Ensure OpenAI API key is available
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key is not configured"
        )

    try:
        # Step 5: Initialize the Speech-to-Text service
        stt_service = SpeechToTextService(api_key=OPENAI_API_KEY)

        # Step 6: Perform speech-to-text conversion
        text, language = stt_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file.filename
        )

        # Step 7: Return the structured response
        return STTResponse(
            text=text,
            language=language
        )

    except RuntimeError as error:
        # Step 8: Catch STT-related errors and return a clean HTTP error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        )


@router.post(
    "/tts",
    status_code=status.HTTP_200_OK,
    summary="Convert text to speech",
    description=(
        "Send text and receive audio file. "
        "Used for reading medicine reminders and confirmations aloud."
    ),
    responses={
        200: {
            "description": "Audio file generated successfully",
            "content": {
                "audio/mpeg": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            }
        }
    }
)
async def text_to_speech(request: TTSRequest):
    """
    Text-to-Speech endpoint.
    
    This endpoint converts text into speech audio (MP3 format).
    
    Step-by-step process:
    1. Receive text from request
    2. Validate text is not empty
    3. Initialize TTS service
    4. Generate audio
    5. Return audio as MP3 file
    
    Parameters:
    - request: TTSRequest containing:
        - text: Text to convert to speech
        - voice: (optional) Voice name (alloy, echo, fable, onyx, nova, shimmer)
        - speed: (optional) Speech speed (0.25 to 4.0, default 1.0)
    
    Returns:
    - Audio file (MP3 format) as binary response
    
    Called by:
    - Mobile app (for elderly users to hear reminders)
    - Frontend (voice confirmations)
    """
    
    # Step 1: Validate that text is provided
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty"
        )
    
    # Step 2: Check if text is too long (OpenAI limit is around 4096 characters)
    if len(request.text) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text is too long (maximum 4000 characters)"
        )
    
    # Step 3: Ensure OpenAI API key is available
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key is not configured"
        )
    
    try:
        # Step 4: Initialize the Text-to-Speech service
        tts_service = TextToSpeechService(api_key=OPENAI_API_KEY)
        
        # Step 5: Generate audio
        # Pass voice and speed from request, or use defaults
        audio_bytes = tts_service.generate_speech(
            text=request.text,
            voice=request.voice if request.voice else "nova",
            speed=request.speed if request.speed else 1.0
        )
        
        # Step 6: Return audio as MP3 file
        # Response with audio/mpeg content type
        # Frontend can play this directly or save as .mp3
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
    
    except ValueError as error:
        # Validation errors (empty text, invalid voice, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )
    
    except RuntimeError as error:
        # TTS service errors (API call failed, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        )
    
    except Exception as error:
        # Any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate speech: {str(error)}"
        )