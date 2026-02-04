"""
tts.py

Text-to-Speech service using OpenAI TTS API.

This service converts text into speech audio.
Used for:
- Reading medicine reminders aloud
- Voice confirmations
- Instructions for elderly users

This file:
- Only generates audio
- Does NOT save files permanently
- Returns audio bytes
"""

from openai import OpenAI
from typing import Optional
import logging

# Setup logging
logger = logging.getLogger(__name__)


class TextToSpeechService:
    """
    TextToSpeechService converts text into speech audio.
    
    Uses OpenAI TTS API which supports multiple voices.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize TTS service.
        
        What happens here:
        - Create OpenAI client with API key
        - Set default voice
        
        Parameters:
        - api_key: OpenAI API key for TTS
        """
        
        logger.info("Initializing Text-to-Speech service...")
        
        # Create OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Default voice (can be changed)
        # Available voices: alloy, echo, fable, onyx, nova, shimmer
        self.default_voice = "nova"  # Female voice, clear and friendly
        
        logger.info(f"TTS service initialized with voice: {self.default_voice}")
    
    def generate_speech(
        self, 
        text: str, 
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> bytes:
        """
        Convert text to speech audio.
        
        What happens here:
        1. Validate input text
        2. Select voice (use default if not specified)
        3. Call OpenAI TTS API
        4. Return audio bytes
        
        Parameters:
        - text: Text to convert to speech
        - voice: Voice name (alloy, echo, fable, onyx, nova, shimmer)
        - speed: Speed of speech (0.25 to 4.0, default 1.0)
        
        Returns:
        - Audio bytes (MP3 format)
        
        Called by:
        - API route in app/api/voice.py (TTS endpoint)
        """
        
        # Step 1: Validate input
        if not text or not text.strip():
            logger.error("Empty text provided for TTS")
            raise ValueError("Text cannot be empty")
        
        # Step 2: Use provided voice or default
        selected_voice = voice if voice else self.default_voice
        
        # Validate voice option
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if selected_voice not in valid_voices:
            logger.warning(f"Invalid voice '{selected_voice}', using default")
            selected_voice = self.default_voice
        
        # Step 3: Validate speed
        if speed < 0.25 or speed > 4.0:
            logger.warning(f"Invalid speed {speed}, using 1.0")
            speed = 1.0
        
        logger.info(f"Generating speech for: '{text[:50]}...'")
        logger.info(f"Voice: {selected_voice}, Speed: {speed}")
        
        try:
            # Step 4: Call OpenAI TTS API
            # Model: tts-1 (faster, cheaper) or tts-1-hd (higher quality)
            response = self.client.audio.speech.create(
                model="tts-1",  # Use tts-1-hd for better quality
                voice=selected_voice,
                input=text,
                speed=speed
            )
            
            # Step 5: Get audio bytes
            # OpenAI returns audio in MP3 format
            audio_bytes = response.content
            
            logger.info(f"Speech generated: {len(audio_bytes)} bytes")
            
            # Step 6: Return audio bytes
            return audio_bytes
            
        except Exception as e:
            # Log error and re-raise
            logger.error(f"TTS generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate speech: {str(e)}")
    
    def generate_reminder_audio(
        self, 
        medicine_name: str, 
        dosage: str,
        time: str
    ) -> bytes:
        """
        Generate speech for medicine reminder.
        
        This is a helper method that creates a properly formatted
        reminder message and converts it to speech.
        
        What happens here:
        1. Create reminder message
        2. Call generate_speech()
        3. Return audio
        
        Parameters:
        - medicine_name: Name of medicine
        - dosage: Dosage (e.g., "500mg")
        - time: Time to take (e.g., "morning", "8:00 AM")
        
        Returns:
        - Audio bytes
        
        Called by:
        - Reminder scheduler (future implementation)
        """
        
        logger.info(f"Creating reminder for: {medicine_name} {dosage}")
        
        # Create friendly reminder message
        # This message is optimized for elderly users
        message = f"Time to take your medicine. {medicine_name}, {dosage}. Please take it now."
        
        # Generate speech with slower speed for clarity
        audio = self.generate_speech(
            text=message,
            voice="nova",  # Clear female voice
            speed=0.9  # Slightly slower for elderly users
        )
        
        return audio
    
    def generate_confirmation_audio(self, message: str) -> bytes:
        """
        Generate confirmation message audio.
        
        Used for confirming user actions like:
        - "Medicine added successfully"
        - "Appointment scheduled"
        - "Reminder set"
        
        Parameters:
        - message: Confirmation message
        
        Returns:
        - Audio bytes
        """
        
        logger.info(f"Creating confirmation: {message}")
        
        # Generate speech with friendly voice
        audio = self.generate_speech(
            text=message,
            voice="nova",
            speed=1.0
        )
        
        return audio