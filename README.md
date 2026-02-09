
# Med-AI Service – API Documentation

AI-powered backend service for Speech-to-Text (STT), Text-to-Speech (TTS),
Optical Character Recognition (OCR), and Medical Data Extraction.

---

## Core Capabilities

- Voice → Text (STT)
- Text → Voice (TTS)
- Prescription Image / PDF → Structured Medical Data
- Lab Report → Structured Test Results
- Universal AI Chat (Text / Voice / File)

---

## System Architecture Overview

User  
↓  
Frontend (Web / Mobile App)  
↓  
Med-AI Service  
↓  
Backend / Database API  

---

## API Base URL


---

## Health Check

### GET `/health`

Checks whether the Med-AI service is running.

**Response**
```json
{
  "status": "ok"
}
Voice APIs
POST /voice/stt

Convert speech to text.

Request

multipart/form-data

file: audio.wav / audio.mp3

Response

{
  "text": "I need to add Paracetamol 500mg twice daily",
  "language": "en"
}

POST /voice/tts

Convert text to speech.

Request

{
  "text": "Time to take your Paracetamol 500mg",
  "voice": "nova",
  "speed": 1
}


Response

MP3 audio (binary)

OCR API
POST /ocr/extract

Extract raw text from image or PDF.

Request

multipart/form-data

file: prescription.png / prescription.pdf

Response

{
  "raw_text": "DD FORM 1289...\nSig: 5mL tid a.c."
}

Extraction APIs
POST /extract/prescription

AI-readable structured output (for UI/debug).

Request

{
  "raw_text": "Name: John Doe\nAge: 45\nTab. Paracetamol 500mg BD"
}

POST /extract/prescription-backend (MAIN)

Backend database–ready prescription format.

Request

{
  "raw_text": "DD FORM 1289...",
  "user_id": 1,
  "doctor_id": 1,
  "prescription_image_url": "http://localhost:8000/media/prescriptions/1.png"
}



{
  "users": 1,
  "doctor": 1,
  "before_meal": false,
  "after_meal": true,
  "patient": {
    "name": "John Doe",

    "age": 45
  },
  "medicines": [
    {
      "name": "Paracetamol",
      "how_many_time": 2,
      "how_many_day": 7,

      "stock": 14
    }
  ]
}


POST /extract/prescription-django

Django backend compatible format.


POST /extract/voice-intent

Extract intent from voice transcription.

Request

{
  "raw_text": "Add Napa twice daily for 7 days"
}


Response

{
  "intent": "add_medicine",
  "confidence": 0.9
}

POST /extract/lab-report


Extract structured lab test results.

Request

{
  "raw_text": "Blood Sugar: 7.2 mmol/L"
}

Universal AI Chat
POST /ai/chat

Single universal endpoint.

Rule:
Send ONLY ONE input:

text OR

audio OR

file

The AI automatically handles:

STT

OCR

Intent detection

Prescription → backend conversion
