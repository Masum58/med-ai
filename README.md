# Med-AI Service – API Documentation

An AI-powered backend service for Speech-to-Text (STT), Text-to-Speech (TTS),
Optical Character Recognition (OCR), and Medical Data Extraction.

This service enables automated conversion and structuring of medical data
to support healthcare applications.

---

## Core Capabilities

The Med-AI Service converts:

- Voice → Text
- Text → Voice
- Prescription Images → Structured Medical Data
- Lab Reports → Structured Test Results

---

## System Architecture Overview

User Action  
↓  
Frontend (Web / Mobile Application)  
↓  
Med-AI Service (This Project)  
↓  
Backend / Database API  

---

## High-Level Data Flow

### Prescription Processing Flow (Primary Use Case)

Prescription Image  
↓  
`/ocr/extract`  
↓  
Raw Text  
↓  
`/extract/prescription-backend`  
↓  
Backend-Ready JSON  
↓  
Saved to Database  

---

## API Base URL
http://localhost:8000

---

## Health Check API

### GET `/health`

**Purpose**  
Checks whether the Med-AI service is running.

**Response**
```json
{
  "status": "ok"
}

Voice APIs
1️⃣ Speech to Text (STT)

Endpoint

POST /voice/stt


Description
Converts an uploaded audio file into text.

Request

multipart/form-data
file = audio.wav | audio.mp3


Response

{
  "text": "Add Paracetamol 500mg twice daily",
  "language": "en"
}


Note
This output is usually forwarded to /extract/voice-intent.

2️⃣ Text to Speech (TTS)

Endpoint

POST /voice/tts


Request

{
  "text": "Please take your medicine now",
  "voice": "nova",
  "speed": 0.9
}


Response
MP3 audio file (binary)

Use Cases

Medicine reminders

Voice confirmations for elderly users

OCR API
3️⃣ OCR Extraction

Endpoint

POST /ocr/extract


Description
Extracts raw text from prescription images or PDFs.

Request

multipart/form-data
file = prescription.png | prescription.pdf


Response

{
  "raw_text": "DD FORM 1289...\nSig: 5mL tid a.c."
}


Important

Output is unstructured

Must be sent to Extraction APIs

Extraction APIs (AI Core)
4️⃣ Prescription Extraction (AI Format)

Endpoint
POST /extract/prescription


Purpose

Debugging


UI display

Not for database storage

Request

{
  "raw_text": "DD FORM 1289...\nSig: 5mL tid a.c."
}


5️⃣ Prescription Extraction (Backend Format – MAIN)

Endpoint

POST /extract/prescription-backend


Description
Main production endpoint.
Returns backend database–ready JSON.

Request


{
  "raw_text": "DD FORM 1289...\nSig: 5mL tid a.c.",
  "user_id": 1,
  "doctor_id": 1,
  "prescription_image_url": "http://localhost:8000/media/prescriptions/1.png"
}


Backend-Ready Response

{
  "users": 1,
  "doctor": 1,
  "prescription_image": "http://localhost:8000/media/prescriptions/1.png",
  "before_meal": false,

  "after_meal": true,
  "patient": {
    "name": "John Doe",
    "age": 45,
    "sex": null,
    "health_issues": "Gastritis"
  },
  "medicines": [
    {
      "name": "Paracetamol",
      "how_many_time": 2,
      "how_many_day": 7,
      "stock": 14
    }
  ],
  "medical_tests": []
}


Notes

Matches backend DB schema

Can be saved directly without modification

6️⃣ Voice Intent Extraction

Endpoint

POST /extract/voice-intent


Request

{
  "raw_text": "Add Napa twice daily for 7 days"
}


Response

{
  "intent": "add_medicine",
  "confidence": 0.9,
  "data": {
    "medicine_name": "Napa",
    "frequency": "twice daily"
  },
  "confirmation_needed": true,
  "confirmation_message": "Do you want to add Napa twice daily?"
}

7️⃣ Lab Report Extraction

Endpoint

POST /extract/lab-report


Request

{
  "raw_text": "Blood Sugar: 7.2 mmol/L"
}


Response

{
  "tests": [
    {
      "test_name": "Blood Sugar",
      "value": "7.2",
      "unit": "mmol/L",
      "status": "high"
    }
  ]
}
