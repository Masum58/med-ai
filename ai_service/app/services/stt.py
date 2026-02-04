"""
stt.py

Speech-to-Text service with safe error handling.
"""

from openai import OpenAI
from typing import Tuple
import io


class SpeechToTextService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> Tuple[str, str]:
        """
        Convert audio bytes into text using OpenAI STT.

        Returns:
        - text: extracted text
        - language: detected language (if available)
        """

        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename

            response = self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1"
            )

            text = response.text.strip()
            language = getattr(response, "language", "unknown")

            return text, language

        except Exception as e:
            # Re-raise exception so FastAPI shows proper error
            raise RuntimeError(f"Speech-to-Text failed: {str(e)}")
