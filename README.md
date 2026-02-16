🚀 Med-AI Service

AI-powered backend orchestration service for medical workflows.

🧠 What This Service Does

Med-AI is an AI microservice that handles:

🎤 Speech to Text (STT)

🔊 Text to Speech (TTS)

🖼 OCR (Image/PDF → Text)

💊 Prescription Extraction (AI → Structured Data)

🎯 Intent Detection

🤖 Universal AI Chat Orchestration

📖 Database READ (GET only)

⚠️ Architecture Rule (Very Important)

This service:

❌ Does NOT save data to database

❌ Does NOT modify backend records

✅ ONLY reads database (GET)

✅ Prepares structured data for backend

✅ Returns orchestration response

✅ Provides TTS instructions (audio generated separately)

Database save operations must be handled by the main backend system.

🛠 Installation Guide
1️⃣ Clone Repository
git clone https://github.com/your-username/Med-AI.git
cd Med-AI/ai_service

2️⃣ Create Virtual Environment
Windows
python -m venv venv
venv\Scripts\activate

macOS / Linux
python3 -m venv venv
source venv/bin/activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Configure Environment Variables

Create a .env file inside ai_service/:

OPENAI_API_KEY=your_openai_api_key_here
DJANGO_ACCESS_TOKEN=your_backend_access_token

▶️ Run the Application
Windows
python run.py


OR

python -m uvicorn app.main:app --reload

macOS / Linux
uvicorn app.main:app --reload

🌍 Application URLs

Local Server:

http://localhost:8000


Swagger Docs:

http://localhost:8000/docs

📡 API Overview
🩺 Health Check
GET /health


Response:

{
  "status": "ok"
}

🎤 Voice APIs
🔹 Speech to Text
POST /voice/stt


Request: multipart/form-data
file = audio.wav / audio.mp3

Response:

{
  "text": "I need to add Paracetamol 500mg twice daily",
  "language": "en"
}

🔹 Text to Speech
POST /voice/tts


Request:

{
  "text": "Time to take your medicine",
  "voice": "nova",
  "speed": 1
}


Response:
MP3 audio file (binary)

🖼 OCR API
POST /ocr/extract


Extract raw text from image or PDF.

Request: multipart/form-data
file = prescription.png

Response:

{
  "raw_text": "Name: John Doe\nTab. Paracetamol 500mg BD"
}

🧾 Extraction APIs
🔹 AI Structured Format (UI Friendly)
POST /extract/prescription

🔹 Backend Ready Format (MAIN)
POST /extract/prescription-backend


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
  "medicines": []
}

🎯 Intent Detection
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

🤖 Universal AI Chat (Core Endpoint)
POST /ai/chat

🔥 Rule:

Send ONLY ONE input:

JSON body (text mode)

audio file (voice mode)

file (prescription mode)

🟢 Text Mode (Postman → raw → JSON)
{
  "text": "Give me today's medicines",
  "user_id": 6,
  "reply_mode": "both"
}

🟢 Voice Mode (form-data)

audio = recording.m4a

user_id = 6

reply_mode = voice

🟢 Prescription Mode (form-data)

file = prescription.jpg

user_id = 6

reply_mode = text

🧠 AI Automatically Handles

STT

OCR

Intent detection

Prescription → backend-ready conversion

Secure DB READ (GET only)

Human-friendly response

TTS instruction payload

Example Response
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


Frontend must call /voice/tts separately to generate audio.

🔐 Production Notes

JWT authentication required for database access

AI never stores sensitive data

Token-based secure backend communication

TTS generation separated for scalability

Designed for microservice architecture

🏗 Architecture Summary
Frontend
   ↓
AI Service (This Repo)
   ↓
Backend API (Django / DRF)
   ↓
Database


AI prepares.
Backend saves.
Frontend orchestrates.