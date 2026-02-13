Med-AI Service

AI-powered backend service for:

Speech to Text (STT)

Text to Speech (TTS)

OCR (Image/PDF → Text)

Prescription extraction

Intent detection

Universal AI Chat Orchestration

This service does NOT save data directly to the database.
Database save operations must be handled by the backend system.

1. Installation Guide
Clone Repository
git clone https://github.com/your-username/med-ai-service.git
cd med-ai-service

2. Create Virtual Environment
Windows
python -m venv venv
venv\Scripts\activate

macOS / Linux
python3 -m venv venv
source venv/bin/activate

3. Install Dependencies
pip install -r requirements.txt

4. Configure Environment Variables

Create a .env file in project root:

OPENAI_API_KEY=your_openai_api_key_here

5. Run the Application
Windows

If uvicorn is not recognized, use:

python run.py


Or:

python -m uvicorn app.main:app --reload

macOS
uvicorn app.main:app --reload


If uvicorn is not recognized:

python3 -m uvicorn app.main:app --reload


Application will run at:

http://localhost:8000


Swagger documentation:

http://localhost:8000/docs

API Documentation

Base URL:

http://localhost:8000

Health Check

GET /health

Response:

{
  "status": "ok"
}

Voice APIs
POST /voice/stt

Convert speech to text.

Request:

multipart/form-data

file: audio.wav / audio.mp3


Response:

{
  "text": "I need to add Paracetamol 500mg twice daily",
  "language": "en"
}

POST /voice/tts

Convert text to speech.

Request:

{
  "text": "Time to take your Paracetamol 500mg",
  "voice": "nova",
  "speed": 1
}


Response:

MP3 audio file (binary)

OCR API
POST /ocr/extract

Extract raw text from image or PDF.

Request:

multipart/form-data

file: prescription.png / prescription.pdf


Response:

{
  "raw_text": "DD FORM 1289...\nSig: 5mL tid a.c."
}

Extraction APIs
POST /extract/prescription

AI-readable structured output (for UI/debug).

Request:

{
  "raw_text": "Name: John Doe\nAge: 45\nTab. Paracetamol 500mg BD"
}

POST /extract/prescription-backend (MAIN)

Backend database-ready format.

Request:

{
  "raw_text": "...",
  "user_id": 1,
  "doctor_id": 1,
  "prescription_image_url": "http://localhost/image.png"
}


Response:

{
  "users": 1,
  "doctor": 1,
  "patient": {
    "name": "John Doe",
    "age": 45
  },
  "medicines": [...]
}

Intent Extraction
POST /extract/voice-intent

Request:

{
  "raw_text": "Add Napa twice daily for 7 days"
}


Response:

{
  "intent": "add_medicine",
  "confidence": 0.9
}

Universal AI Chat
POST /ai/chat

Single universal endpoint for end users.

Rule:

Send ONLY ONE input:

text

OR audio

OR file

AI automatically handles:

STT

OCR

Intent detection

Prescription → backend-ready conversion

Database READ (GET only)

Human-friendly response

TTS instruction

AI NEVER saves data directly.

Example Request
POST /ai/chat?text=How many medicines are left?&user_id=1&reply_mode=both


Response:

{
  "assistant_message": "You have 2 medicines running low.",
  "tts": {
    "endpoint": "/voice/tts",
    "method": "POST",
    "payload": {
      "text": "You have 2 medicines running low.",
      "voice": "nova",
      "speed": 0.9
    }
  }
}


Frontend must call /voice/tts using the payload to generate the audio.

Important Architecture Notes

AI service does NOT save to database

Database save must be triggered explicitly by backend/frontend

AI only prepares data and reads data

TTS audio generation is separated for scalability

Secure token-based authentication must be added before production deployment