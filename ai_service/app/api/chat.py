"""
chat.py

UNIVERSAL AI CHAT ENDPOINT (OPTION B – PRODUCTION SAFE)

IMPORTANT DESIGN PRINCIPLES
---------------------------
• User calls ONLY this endpoint
• AI service NEVER saves data directly to database
• AI service ONLY:
  - Understands user input
  - Converts voice/image → text
  - Detects user intent
  - Prepares database-ready data (but does NOT save)
  - Reads data from database (GET only)
  - Generates human-friendly reply
  - Instructs frontend when to use TTS

DATABASE SAVE is ALWAYS handled by:
→ Frontend or Backend service (NOT AI)
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Optional
import requests

from app.services.stt import SpeechToTextService
from app.services.ocr import OCRService
from app.services.extractor import AIExtractorService
from app.config import OPENAI_API_KEY

router = APIRouter()

# ------------------------------------------------------------------
# TEMPORARY DATABASE API BASE
# NOTE:
# Database developer has not provided auth token yet.
# This MUST be secured with token-based auth before production.
# ------------------------------------------------------------------
DATABASE_API_BASE = "https://medicalai.pythonanywhere.com/api"


@router.post(
    "/chat",
    summary="Universal AI Chat (Text / Voice / Prescription)",
    description="""
Single universal AI endpoint for end users.

User must send EXACTLY ONE input:
• text  → normal chat
• audio → voice command
• file  → prescription / document

AI handles internally:
• STT (Speech to Text)
• OCR (Image/PDF to Text)
• Intent detection
• Prescription → database-ready conversion
• Database READ (GET only)
• Human-friendly reply
• Optional Text-to-Speech instruction

AI NEVER saves data directly to database.
"""
)
async def ai_chat(
    # --------------------------------------------------
    # USER INPUT (ONLY ONE IS ALLOWED)
    # --------------------------------------------------
    text: Optional[str] = Query(
        None,
        description="Typed message. Use ONLY for text chat."
    ),

    audio: Optional[UploadFile] = File(
        None,
        description="Voice input (mp3/wav). Use ONLY for voice commands."
    ),

    file: Optional[UploadFile] = File(
        None,
        description="Prescription image or PDF document."
    ),

    # --------------------------------------------------
    # CONTEXT
    # --------------------------------------------------
    user_id: Optional[int] = Query(
        None,
        description="Logged-in user ID. Required for database READ."
    ),

    reply_mode: str = Query(
        "text",
        description="Response type: text | voice | both"
    )
):
    # --------------------------------------------------
    # STEP 0: STRICT INPUT VALIDATION
    # --------------------------------------------------
    provided_inputs = [
        bool(text and text.strip()),
        bool(audio),
        bool(file)
    ]

    if sum(provided_inputs) != 1:
        raise HTTPException(
            status_code=400,
            detail="Provide EXACTLY ONE input: text OR audio OR file"
        )

    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="AI service is not configured"
        )

    # --------------------------------------------------
    # NORMALIZE reply_mode (PRODUCTION SAFETY)
    # --------------------------------------------------
    reply_mode = reply_mode.strip().lower()

    # --------------------------------------------------
    # STEP 1: CONVERT INPUT → PLAIN TEXT
    # --------------------------------------------------
    final_text = ""
    input_type = "text"

    # Voice → STT
    if audio:
        input_type = "voice"
        audio_bytes = await audio.read()

        stt_service = SpeechToTextService(api_key=OPENAI_API_KEY)
        final_text, _ = stt_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename
        )

    # File → OCR
    elif file:
        input_type = "prescription"
        file_bytes = await file.read()

        ocr_service = OCRService(openai_api_key=OPENAI_API_KEY)
        final_text = ocr_service.extract_text(
            file_bytes=file_bytes,
            filename=file.filename
        )

    # Text
    else:
        final_text = text.strip()

    # --------------------------------------------------
    # STEP 2: INTENT DETECTION (AI BRAIN)
    # --------------------------------------------------
    extractor = AIExtractorService(api_key=OPENAI_API_KEY)
    intent_result = extractor.extract_voice_intent(final_text)

    intent = intent_result.get("intent")
    confidence = intent_result.get("confidence")
    backend_action = intent_result.get("database_action")

    # --------------------------------------------------
    # STEP 3: PRESCRIPTION → DATABASE-READY DATA
    # (NO SAVE — PREPARE ONLY)
    # --------------------------------------------------
    structured_data = None

    if input_type == "prescription":
        structured_data = extractor.extract_prescription_data(
            raw_text=final_text,
            return_backend_format=True,
            user_id=user_id
        )

    # --------------------------------------------------
    # STEP 4: DATABASE READ (GET ONLY)
    # --------------------------------------------------
    db_data = None

    if backend_action and user_id:
        try:
            # Example backend_action:
            # "GET /prescriptions/my_prescriptions/"
            endpoint = backend_action["api_endpoint"].replace("GET ", "")
            url = DATABASE_API_BASE + endpoint

            params = backend_action.get("query_filters", {})
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            db_data = response.json()

        except Exception:
            # Fail-safe: AI should never break user experience
            db_data = None

    # --------------------------------------------------
    # STEP 5: HUMAN-FRIENDLY MESSAGE
    # --------------------------------------------------
    assistant_message = intent_result.get(
        "user_response",
        "I understood your request."
    )

    # Example: Refill medicine flow
    if intent == "refill_medicine" and db_data:
        lines = []
        lines.append(f"You have {len(db_data)} medicines running low.")

        for med in db_data:
            lines.append(
                f"{med['name']} has {med['stock']} tablets left."
            )

        lines.append("Would you like to refill any of them?")
        assistant_message = " ".join(lines)

    # --------------------------------------------------
    # STEP 6: TTS INSTRUCTION (NO AUDIO DATA)
    # --------------------------------------------------
    tts_payload = None

    if reply_mode in ["voice", "both"]:
        tts_payload = {
            "enabled": True,
            "endpoint": "/voice/tts",
            "method": "POST",
            "payload": {
                "text": assistant_message,
                "voice": "nova",
                "speed": 0.9
            }
        }


    # --------------------------------------------------
    # STEP 7: FINAL RESPONSE (CLEAN & PRODUCTION SAFE)
    # --------------------------------------------------
    return {
        "success": True,
        "input_type": input_type,

        "intent": intent,
        "confidence": confidence,

        # AI-prepared data (frontend decides SAVE)
        "data": structured_data,

        # Backend read transparency
        "backend_action": backend_action,
        "db_data": db_data,

        # Human-readable response
        "assistant_message": assistant_message,

        # TTS instruction (frontend calls /voice/tts)
        "tts": tts_payload,

        "confirmation_needed": intent_result.get(
            "confirmation_needed", False
        )
    }
