"""
chat.py

UNIVERSAL AI CHAT ENDPOINT (PRODUCTION SAFE)

- AI NEVER saves to database
- AI ONLY reads database (GET)
- AI returns clean orchestration response

ONE ENDPOINT - 3 modes:
1. TEXT:         POST /ai/chat  →  raw JSON body
2. VOICE:        POST /ai/chat  →  form-data with audio file
3. PRESCRIPTION: POST /ai/chat  →  form-data with image file
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from typing import Optional
from enum import Enum
from pydantic import BaseModel
import requests
import json

from app.services.stt import SpeechToTextService
from app.services.ocr import OCRService
from app.services.extractor import AIExtractorService
from app.config import OPENAI_API_KEY

router = APIRouter()


# --------------------------------------------------
# ENUMS & MODELS
# --------------------------------------------------
class ReplyMode(str, Enum):
    text = "text"
    voice = "voice"
    both = "both"


# --------------------------------------------------
# DATABASE API BASE
# --------------------------------------------------
DATABASE_API_BASE = "https://test15.fireai.agency"



# --------------------------------------------------
# SINGLE ENDPOINT
# --------------------------------------------------
@router.post(
    "/chat",
    summary="Universal AI Chat (Text / Voice / Prescription)",
    description=(
        "ONE endpoint for all 3 modes.\n\n"
        "TEXT MODE - Postman Body → raw → JSON:\n"
        '{"text": "Give me today medicines", "user_id": 4, "reply_mode": "text"}\n\n'
        "VOICE MODE - Postman Body → form-data:\n"
        "audio = Recording.m4a, user_id = 4, reply_mode = voice\n\n"
        "PRESCRIPTION MODE - Postman Body → form-data:\n"
        "file = prescription.jpg, user_id = 4, reply_mode = text"
    ),
    tags=["AI Chat"]
)
async def ai_chat(
    request: Request,
    audio: Optional[UploadFile] = File(None, description="Audio file (.m4a .mp3 .wav) for voice mode"),
    file: Optional[UploadFile] = File(None, description="Prescription image (PNG JPG PDF) for prescription mode"),
):
    """
    TEXT MODE - Postman:
        Body → raw → JSON
        {"text": "Give me today's medicines", "user_id": 4, "reply_mode": "text"}

    VOICE MODE - Postman:
        Body → form-data
        audio    = [select audio file]
        user_id  = 4
        reply_mode = voice

    PRESCRIPTION MODE - Postman:
        Body → form-data
        file     = [select image]
        user_id  = 4
        reply_mode = text
    """

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="AI service not configured")

    # --------------------------------------------------
    # PARSE INPUT - JSON or form-data
    # --------------------------------------------------
    text = None
    user_id = None
    reply_mode = ReplyMode.text

    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        # TEXT MODE: raw JSON body
        try:
            body = await request.json()
            text = body.get("text")
            user_id = body.get("user_id")
            reply_mode = ReplyMode(body.get("reply_mode", "text"))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail='Invalid JSON. Example: {"text": "your message", "user_id": 4, "reply_mode": "text"}'
            )

    else:
        # VOICE/PRESCRIPTION MODE: form-data
        try:
            form = await request.form()
            user_id_str = form.get("user_id")
            user_id = int(user_id_str) if user_id_str else None
            reply_mode_str = form.get("reply_mode", "text")
            reply_mode = ReplyMode(reply_mode_str)
        except Exception:
            user_id = None
            reply_mode = ReplyMode.text

    # --------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------
    audio_provided = bool(audio and audio.filename and audio.filename.strip())
    file_provided = bool(file and file.filename and file.filename.strip())
    text_provided = bool(text and str(text).strip())

    provided_inputs = [text_provided, audio_provided, file_provided]

    if sum(provided_inputs) != 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide EXACTLY ONE input: "
                "JSON body with text OR audio file OR prescription file"
            )
        )

    # --------------------------------------------------
    # CONVERT INPUT TO TEXT
    # --------------------------------------------------
    final_text = ""
    input_type = "text"

    SUPPORTED_AUDIO = [
        ".flac", ".m4a", ".mp3", ".mp4",
        ".mpeg", ".mpga", ".oga", ".ogg",
        ".wav", ".webm"
    ]

    try:
        if audio_provided:
            # Validate audio format
            audio_ext = "." + audio.filename.split(".")[-1].lower()
            if audio_ext not in SUPPORTED_AUDIO:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported audio format. Supported: {SUPPORTED_AUDIO}"
                )
            input_type = "voice"
            audio_bytes = await audio.read()
            stt_service = SpeechToTextService(api_key=OPENAI_API_KEY)
            final_text, _ = stt_service.transcribe_audio(
                audio_bytes=audio_bytes,
                filename=audio.filename
            )

        elif file_provided:
            input_type = "prescription"
            file_bytes = await file.read()
            ocr_service = OCRService(openai_api_key=OPENAI_API_KEY)
            final_text = ocr_service.extract_text(
                file_bytes=file_bytes,
                filename=file.filename
            )

        else:
            final_text = str(text).strip()

    except HTTPException:
        raise
    except Exception as e:
        print("REAL STT/OCR ERROR:",e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # --------------------------------------------------
    # INTENT DETECTION
    # --------------------------------------------------
    extractor = AIExtractorService(api_key=OPENAI_API_KEY)

    try:
        intent_result = extractor.extract_voice_intent(final_text)
    except Exception:
        raise HTTPException(status_code=500, detail="AI intent detection failed")

    intent = intent_result.get("intent")
    confidence = intent_result.get("confidence", 0)
    backend_action = intent_result.get("database_action")

    # --------------------------------------------------
    # PRESCRIPTION → STRUCTURED DATA
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
    # DATABASE READ (SAFE + TIMEOUT)
    # --------------------------------------------------
    # --------------------------------------------------
    # DATABASE READ (SAFE + TIMEOUT)
    # --------------------------------------------------
    db_data = None

    # Get Authorization header from frontend
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if backend_action and user_id:
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authorization header missing"
            )
        try:
            endpoint = backend_action.get("api_endpoint", "")

            if "/prescriptions/my_prescriptions/" in endpoint:
                endpoint = "/treatments/prescription"

            if endpoint.startswith("GET "):
                endpoint = endpoint.replace("GET ", "")

            url = DATABASE_API_BASE + endpoint
            params = backend_action.get("query_filters", {})

            print("FINAL URL:", url)

            response = requests.get(
                url,
                params=params,
                headers={
                    "Authorization": auth_header
                },
                timeout=5
            )

            response.raise_for_status()
            db_data = response.json()

        except Exception as e:
            print("DATABASE ERROR:", e)
            db_data = None

    
    # --------------------------------------------------
    # HUMAN-FRIENDLY MESSAGE
    # --------------------------------------------------
    assistant_message = intent_result.get(
    "user_response",
    "I understood your request."
    )
    #  GENERAL AI FALLBACK
    if intent == "unclear":
        assistant_message = extractor.generate_general_response(final_text)
        backend_action = None
        db_data = None

    #  SMART MEDICINE FORMATTER
    #  SMART MEDICINE FORMATTER
    if intent == "check_reminder" and isinstance(db_data, list):

        try:
            time_filter = None

            if backend_action:
                time_filter = backend_action.get("query_filters", {}).get("time_of_day")

            if not db_data:
                assistant_message = "You don't have any medicines scheduled for today."
            else:
                lines = []

                if time_filter:
                    lines.append(f"Here are your {time_filter} medicines:\n")
                else:
                    lines.append("Here are today's medicines:\n")

                for prescription in db_data:
                    for med in prescription.get("medicines", []):
                        name = med.get("name", "Unknown")
                        stock = med.get("stock", 0)

                        schedule_parts = []

                        periods = ["morning", "afternoon", "evening", "night"]

                        #  APPLY FILTER
                        if time_filter:
                            periods = [time_filter]

                        for period in periods:
                            period_data = med.get(period)

                            if period_data:
                                time = period_data.get("time")
                                before = period_data.get("before_meal")
                                after = period_data.get("after_meal")

                                meal_text = ""
                                if before:
                                    meal_text = "before meal"
                                elif after:
                                    meal_text = "after meal"

                                schedule_parts.append(
                                    f"{period} at {time} ({meal_text})"
                                )

                        if schedule_parts:
                            schedule_text = ", ".join(schedule_parts)
                            lines.append(
                                f"- {name} → {schedule_text} | Stock: {stock}"
                            )

                if len(lines) == 1:
                    assistant_message = "You don't have any medicines scheduled for this time."
                else:
                    assistant_message = "\n".join(lines)

        except Exception as e:
            print("FORMAT ERROR:", e)
    

    


    # Refill enrichment
    if intent == "refill_medicine" and isinstance(db_data, list):

        if not db_data:
            assistant_message = "All your medicines have sufficient stock."
        else:
            try:
                lines = [f"You have {len(db_data)} medicines running low."]
                for med in db_data:
                    name = med.get("name", "Unknown medicine")
                    stock = med.get("stock", 0)
                    lines.append(f"{name} has {stock} tablets left.")
                lines.append("Would you like to refill any of them?")
                assistant_message = " ".join(lines)
            except Exception:
                pass


    # --------------------------------------------------
    # TTS ORCHESTRATION
    # --------------------------------------------------
    # --------------------------------------------------
    # TTS ORCHESTRATION (Production Safe)
    # --------------------------------------------------
    tts_payload = None

    if reply_mode in [ReplyMode.voice, ReplyMode.both]:

        tts_text = assistant_message.strip()

        MAX_TTS_LENGTH = 1300
        SAFE_TTS_LENGTH = 1100

        if len(tts_text) > MAX_TTS_LENGTH:
            tts_text = tts_text[:SAFE_TTS_LENGTH].rstrip()

            # Avoid cutting mid-sentence
            last_dot = tts_text.rfind(".")
            if last_dot > 200:
                tts_text = tts_text[:last_dot + 1]

            tts_text += " Please check the full details in your app."

        tts_payload = {
            "enabled": True,
            "endpoint": "/voice/tts",
            "method": "POST",
            "payload": {
                "text": tts_text,
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
        "confirmation_needed": intent_result.get("confirmation_needed", False)
    }