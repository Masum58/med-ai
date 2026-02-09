"""
chat.py

UNIVERSAL AI CHAT ENDPOINT (PRODUCTION VERSION)

This endpoint is designed for NORMAL USERS, not developers.

User can interact with AI in ONLY ONE way at a time:
- Type a message (text)
- Speak (audio)
- Upload prescription/document (file)

The system will automatically:
- Convert voice to text (STT)
- Extract text from image/PDF (OCR)
- Understand user intent
- If prescription is detected → convert to DATABASE-READY format
- Decide which backend API should be called
- Generate a human-friendly reply
- Optionally return voice reply (TTS)

Frontend needs to call ONLY THIS endpoint.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Optional
import base64

from app.services.stt import SpeechToTextService
from app.services.tts import TextToSpeechService
from app.services.ocr import OCRService
from app.services.extractor import AIExtractorService
from app.config import OPENAI_API_KEY

router = APIRouter()


@router.post(
    "/chat",
    summary="Universal AI Chat (Text / Voice / Prescription)",
    description="""
This is a SINGLE universal AI endpoint.

IMPORTANT RULE:
You must provide ONLY ONE input:
- text (typed message)
- OR audio (voice message)
- OR file (image/PDF document)

DO NOT send multiple inputs together.

Examples:
- Text chat → send only `text`
- Voice assistant → send only `audio`
- Prescription scan → send only `file`

The AI will automatically handle:
STT, OCR, intent detection,
prescription → database conversion,
backend routing instructions,
and optional voice reply.
"""
)
async def ai_chat(
    # -------------------------------------------------
    # USER INPUT (ONLY ONE)
    # -------------------------------------------------
    text: Optional[str] = Query(
        default=None,
        description="User typed message. Use ONLY for text chat. Do NOT send audio or file."
    ),

    audio: Optional[UploadFile] = File(
        default=None,
        description="User voice recording (mp3/wav). Use ONLY for voice input."
    ),

    file: Optional[UploadFile] = File(
        default=None,
        description="Prescription image or PDF. Use ONLY for document upload."
    ),

    # -------------------------------------------------
    # OPTIONAL CONTEXT
    # -------------------------------------------------
    user_id: Optional[int] = Query(
        default=None,
        description="Logged-in user ID. Optional but required for DB fetch/save."
    ),

    reply_mode: str = Query(
        default="text",
        description="How AI should reply: text | voice | both."
    )
):
    """
    INTERNAL FLOW (Readable by non-developers):

    1. Ensure user sent EXACTLY ONE input
    2. Convert input into plain text
    3. Ask AI what the user wants (intent)
    4. If prescription → extract DATABASE-READY data
    5. Prepare human-friendly reply
    6. Optionally convert reply to voice
    """

    # -------------------------------------------------
    # STEP 0: Validate correct input usage
    # -------------------------------------------------
    provided_inputs = [
        bool(text and text.strip()),
        bool(audio),
        bool(file)
    ]

    if sum(provided_inputs) == 0:
        raise HTTPException(
            status_code=400,
            detail="You must provide ONE input: text OR audio OR file"
        )

    if sum(provided_inputs) > 1:
        raise HTTPException(
            status_code=400,
            detail="Provide ONLY ONE input. Do not send text, audio, or file together."
        )

    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI service is not configured"
        )

    # -------------------------------------------------
    # STEP 1: Convert input into plain text
    # -------------------------------------------------
    final_text = ""
    input_type = "text"

    # Voice input
    if audio:
        input_type = "voice"
        audio_bytes = await audio.read()

        stt_service = SpeechToTextService(api_key=OPENAI_API_KEY)
        final_text, _ = stt_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename
        )

    # File input (image / PDF)
    elif file:
        input_type = "prescription"
        file_bytes = await file.read()

        ocr_service = OCRService(openai_api_key=OPENAI_API_KEY)
        final_text = ocr_service.extract_text(
            file_bytes=file_bytes,
            filename=file.filename
        )

    # Text input
    else:
        final_text = text.strip()

    # -------------------------------------------------
    # STEP 2: Understand user intent
    # -------------------------------------------------
    extractor = AIExtractorService(api_key=OPENAI_API_KEY)
    intent_result = extractor.extract_voice_intent(final_text)

    intent = intent_result.get("intent")
    confidence = intent_result.get("confidence")

    # -------------------------------------------------
    # STEP 3: PRESCRIPTION → DATABASE FORMAT (CRITICAL)
    # -------------------------------------------------
    structured_data = None

    # If input is prescription OR intent clearly refers to prescription
    if input_type == "prescription" or intent in ["view_prescription", "add_medicine"]:
        structured_data = extractor.extract_prescription_data(
            raw_text=final_text,
            return_backend_format=True,
            user_id=user_id
        )

    # -------------------------------------------------
    # STEP 4: Prepare assistant reply
    # -------------------------------------------------
    assistant_message = intent_result.get(
        "user_response",
        "I understood your request."
    )

    # -------------------------------------------------
    # STEP 5: Optional voice reply
    # -------------------------------------------------
    audio_reply_base64 = None

    if reply_mode in ["voice", "both"]:
        tts_service = TextToSpeechService(api_key=OPENAI_API_KEY)

        audio_bytes = tts_service.generate_speech(
            text=assistant_message,
            voice="nova",
            speed=0.9
        )

        audio_reply_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    # -------------------------------------------------
    # STEP 6: FINAL RESPONSE (PRODUCTION SAFE)
    # -------------------------------------------------
    return {
        "success": True,

        # What kind of input this was
        "input_type": input_type,

        # AI understanding
        "intent": intent,
        "confidence": confidence,

        # DATABASE-READY DATA (only when applicable)
        "data": structured_data,

        # Backend instruction (frontend should follow, not modify)
        "backend_action": intent_result.get("database_action"),

        # UI hint for frontend
        "ui_action": intent_result.get("ui_action"),

        # Human-friendly reply
        "assistant_message": assistant_message,

        # Optional voice output
        "audio_reply": audio_reply_base64,

        # Conversation control
        "confirmation_needed": intent_result.get("confirmation_needed", False)
    }
