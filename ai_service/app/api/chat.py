"""
chat.py

UNIVERSAL AI CHAT ENDPOINT (OPTION B – PRODUCTION SAFE)

• AI NEVER saves to database
• AI ONLY reads database (GET)
• AI returns clean orchestration response
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Optional
from enum import Enum
import requests

from app.services.stt import SpeechToTextService
from app.services.ocr import OCRService
from app.services.extractor import AIExtractorService
from app.config import OPENAI_API_KEY

router = APIRouter()

# --------------------------------------------------
# ENUM FOR SWAGGER DROPDOWN
# --------------------------------------------------
class ReplyMode(str, Enum):
    text = "text"
    voice = "voice"
    both = "both"


# --------------------------------------------------
# DATABASE API BASE (TEMP – NO AUTH YET)
# --------------------------------------------------
DATABASE_API_BASE = "https://medicalai.pythonanywhere.com/api"


@router.post(
    "/chat",
    summary="Universal AI Chat (Text / Voice / Prescription)",
)
async def ai_chat(
    text: Optional[str] = Query(None),
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    user_id: Optional[int] = Query(None),
    reply_mode: ReplyMode = Query(ReplyMode.text),
):
    # --------------------------------------------------
    # STEP 0: VALIDATE INPUT
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
            detail="AI service not configured"
        )

    # --------------------------------------------------
    # STEP 1: CONVERT INPUT → TEXT
    # --------------------------------------------------
    final_text = ""
    input_type = "text"

    try:
        if audio:
            input_type = "voice"
            audio_bytes = await audio.read()

            stt_service = SpeechToTextService(api_key=OPENAI_API_KEY)
            final_text, _ = stt_service.transcribe_audio(
                audio_bytes=audio_bytes,
                filename=audio.filename
            )

        elif file:
            input_type = "prescription"
            file_bytes = await file.read()

            ocr_service = OCRService(openai_api_key=OPENAI_API_KEY)
            final_text = ocr_service.extract_text(
                file_bytes=file_bytes,
                filename=file.filename
            )

        else:
            final_text = text.strip()

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to process input (STT/OCR error)"
        )

    # --------------------------------------------------
    # STEP 2: INTENT DETECTION
    # --------------------------------------------------
    extractor = AIExtractorService(api_key=OPENAI_API_KEY)

    try:
        intent_result = extractor.extract_voice_intent(final_text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="AI intent detection failed"
        )

    intent = intent_result.get("intent")
    confidence = intent_result.get("confidence", 0)
    backend_action = intent_result.get("database_action")

    # --------------------------------------------------
    # STEP 3: PRESCRIPTION → STRUCTURED DATA
    # --------------------------------------------------
    structured_data = None

    if input_type == "prescription":
        try:
            structured_data = extractor.extract_prescription_data(
                raw_text=final_text,
                return_backend_format=True,
                user_id=user_id
            )
        except Exception:
            structured_data = None

    # --------------------------------------------------
    # STEP 4: DATABASE READ (SAFE + TIMEOUT)
    # --------------------------------------------------
    db_data = None

    if backend_action and user_id:
        try:
            endpoint = backend_action.get("api_endpoint", "")
            if endpoint.startswith("GET "):
                endpoint = endpoint.replace("GET ", "")

            url = DATABASE_API_BASE + endpoint
            params = backend_action.get("query_filters", {})

            response = requests.get(
                url,
                params=params,
                timeout=5  # ⚠ prevent hanging
            )
            response.raise_for_status()

            db_data = response.json()

        except Exception:
            db_data = None  # Never break user flow

    # --------------------------------------------------
    # STEP 5: HUMAN-FRIENDLY MESSAGE
    # --------------------------------------------------
    assistant_message = intent_result.get(
        "user_response",
        "I understood your request."
    )

    # Refill enrichment (SAFE)
    if intent == "refill_medicine" and isinstance(db_data, list):
        try:
            lines = []
            lines.append(f"You have {len(db_data)} medicines running low.")

            for med in db_data:
                name = med.get("name", "Unknown medicine")
                stock = med.get("stock", 0)
                lines.append(f"{name} has {stock} tablets left.")

            lines.append("Would you like to refill any of them?")
            assistant_message = " ".join(lines)

        except Exception:
            pass

    # --------------------------------------------------
    # STEP 6: TTS ORCHESTRATION (NO AUDIO HERE)
    # --------------------------------------------------
    tts_payload = None

    if reply_mode in [ReplyMode.voice, ReplyMode.both]:
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
    # FINAL RESPONSE
    # --------------------------------------------------
    return {
        "success": True,
        "input_type": input_type,
        "intent": intent,
        "confidence": confidence,
        "data": structured_data,
        "backend_action": backend_action,
        "db_data": db_data,
        "assistant_message": assistant_message,
        "tts": tts_payload,
        "confirmation_needed": intent_result.get(
            "confirmation_needed", False
        )
    }
