"""
extractor.py

AI-powered extractor that converts unstructured text
(from OCR or voice) into structured JSON data.

This service uses OpenAI GPT to intelligently parse:
- Medicine names, dosages, frequencies
- Appointment dates, times, doctor names
- Lab test names, values, dates
- Patient information

Updated to include backend format conversion.
"""

from openai import OpenAI
from typing import Dict, Any, Optional
import json
import logging

# Import converter service
from app.services.converter import DataConverterService

# Setup logging
logger = logging.getLogger(__name__)


class AIExtractorService:
    """
    AIExtractorService extracts structured data from unstructured text.
    
    This is the brain of CareAgent AI - it understands:
    - Medical terminology
    - Date/time expressions
    - Dosage formats
    - Appointment context
    """
    
    def __init__(self, api_key: str):
        """
        Initialize AI Extractor service.
        
        Parameters:
        - api_key: OpenAI API key
        """
        
        logger.info("Initializing AI Extractor service...")
        
        # Create OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Create converter instance
        self.converter = DataConverterService()
        
        logger.info("AI Extractor initialized")
    
    def extract_prescription_data(
        self, 
        raw_text: str,
        return_backend_format: bool = False,
        user_id: Optional[int] = None,
        doctor_id: Optional[int] = None,
        prescription_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured prescription data from OCR text.
        
        This method parses prescription text and extracts:
        - Patient name and age
        - Medicine list with dosages and frequencies
        - Doctor information
        - Date of prescription
        
        What happens here:
        1. Send raw text to GPT with specific instructions
        2. GPT analyzes and structures the data
        3. Optionally convert to backend format
        4. Return structured JSON
        
        Parameters:
        - raw_text: Unstructured text from OCR
        - return_backend_format: If True, convert to backend DB format
        - user_id: User ID (required if return_backend_format=True)
        - doctor_id: Doctor ID (required if return_backend_format=True)
        - prescription_image_url: Image URL (required if return_backend_format=True)
        
        Returns:
        - Structured prescription data as dict
        
        Called by:
        - API route when user uploads prescription image
        """
        
        logger.info("Extracting prescription data...")
        logger.info(f"Input length: {len(raw_text)} characters")
        logger.info(f"Backend format: {return_backend_format}")
        
        # Create detailed prompt for GPT
        prompt = f"""You are a medical prescription parser. Extract structured data from this prescription text.

Prescription Text:
{raw_text}

Extract and return ONLY a valid JSON object with this exact structure:
{{
    "patient_name": "full patient name or null",
    "patient_age": age as number or null,
    "prescription_date": "YYYY-MM-DD format or null",
    "doctor_name": "doctor name or null",
    "medicines": [
        {{
            "name": "medicine name (cleaned, no prefix like Tab./Cap.)",
            "type": "Tablet/Capsule/Syrup/Injection or null",
            "dosage": "dosage with unit (e.g., 500mg, 1 tablet)",
            "frequency": "how often (e.g., twice daily, once daily, as needed)",
            "duration": "how long (e.g., 7 days, 2 weeks) or null",
            "instructions": "special instructions (after food, before sleep, etc.) or empty string",
            "refill_needed": true/false (true if long-term medicine)
        }}
    ],
    "diagnosis": "diagnosis/condition if mentioned, or null",
    "advice": "doctor's advice if any, or null"
}}

Rules:
1. Clean medicine names (remove Tab., Cap., Inj., etc.)
2. Parse dates to YYYY-MM-DD format
3. Use null for missing data
4. Extract ALL medicines mentioned
5. Infer frequency from common patterns (BD = twice daily, TDS = thrice daily, etc.)
6. Return ONLY valid JSON, no explanation text
"""
        
        try:
            # Call GPT to extract structured data
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical data extraction expert. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # Get response text
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            elif result_text.startswith("```"):
                result_text = result_text.replace("```", "").strip()
            
            # Parse JSON
            extracted_data = json.loads(result_text)
            
            logger.info(f"Extracted {len(extracted_data.get('medicines', []))} medicines")
            logger.info(f"Patient: {extracted_data.get('patient_name', 'Unknown')}")
            
            # If backend format requested, convert
            if return_backend_format:
                if not all([user_id, doctor_id, prescription_image_url]):
                    raise ValueError("user_id, doctor_id, and prescription_image_url required for backend format")
                
                logger.info("Converting to backend format...")
                backend_data = self.converter.convert_prescription_to_backend(
                    ai_output=extracted_data,
                    user_id=user_id,
                    doctor_id=doctor_id,
                    prescription_image_url=prescription_image_url
                )
                
                return backend_data
            
            # Return AI format
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response was: {result_text[:200]}")
            raise RuntimeError("Failed to extract structured data from prescription")
        
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            raise RuntimeError(f"Failed to extract prescription data: {str(e)}")
    
    def extract_voice_intent(self, transcribed_text: str) -> Dict[str, Any]:
        """
        Extract intent and data from voice input.
        
        This method understands what user wants to do from voice:
        - Add medicine
        - Schedule appointment
        - Ask question
        - Set reminder
        
        What happens here:
        1. Analyze voice transcription
        2. Determine user intent
        3. Extract relevant data
        4. Return structured response
        
        Parameters:
        - transcribed_text: Text from speech-to-text
        
        Returns:
        - Intent and extracted data
        
        Called by:
        - Voice workflow API
        """
        
        logger.info("Extracting intent from voice...")
        logger.info(f"Input: {transcribed_text}")
        
        prompt = f"""You are a voice assistant for elderly users managing their health.

User said: "{transcribed_text}"

Determine what the user wants to do and extract relevant information.

Return ONLY valid JSON with this structure:
{{
    "intent": "add_medicine|schedule_appointment|check_reminder|ask_question|other",
    "confidence": 0.0 to 1.0,
    "data": {{
        "medicine_name": "name or null",
        "dosage": "dosage or null",
        "frequency": "how often or null",
        "instructions": "special notes or null",
        "doctor_name": "name or null",
        "appointment_date": "YYYY-MM-DD or null",
        "appointment_time": "HH:MM or null",
        "reason": "reason or null",
        "query": "user's question or request"
    }},
    "confirmation_needed": true/false,
    "confirmation_message": "Clear confirmation question for user in simple English"
}}

Rules:
1. Use simple, clear confirmation messages
2. If information is incomplete, set confidence lower
3. Always ask for confirmation for add/schedule actions
4. Return ONLY JSON, no explanation
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful voice assistant. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean markdown
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            extracted_intent = json.loads(result_text)
            
            logger.info(f"Intent: {extracted_intent.get('intent')}")
            logger.info(f"Confidence: {extracted_intent.get('confidence')}")
            
            return extracted_intent
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {str(e)}")
            
            # Return fallback response
            return {
                "intent": "unclear",
                "confidence": 0.0,
                "data": {"query": transcribed_text},
                "confirmation_needed": True,
                "confirmation_message": f"I heard: {transcribed_text}. What would you like me to do?"
            }
    
    def extract_lab_report_data(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract structured lab report data.
        
        Parses lab test results and extracts:
        - Test names
        - Values
        - Units
        - Normal ranges
        - Dates
        
        Parameters:
        - raw_text: Unstructured lab report text
        
        Returns:
        - Structured lab data
        
        Called by:
        - API route when user uploads lab PDF
        """
        
        logger.info("Extracting lab report data...")
        
        prompt = f"""You are a medical lab report parser.

Lab Report Text:
{raw_text}

Extract and return ONLY valid JSON:
{{
    "patient_name": "name or null",
    "report_date": "YYYY-MM-DD or null",
    "lab_name": "laboratory name or null",
    "tests": [
        {{
            "test_name": "test name",
            "value": "numeric value as string",
            "unit": "unit (mg/dL, g/dL, etc.)",
            "normal_range": "range or null",
            "status": "normal|high|low or null"
        }}
    ],
    "significant_findings": ["list of abnormal results"],
    "doctor_comments": "comments if any or null"
}}

Rules:
1. Extract ALL tests mentioned
2. Determine status by comparing value with normal range
3. Flag significant findings (high/low values)
4. Return ONLY JSON
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a lab report analyzer. Return only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean markdown
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            
            extracted_data = json.loads(result_text)
            
            logger.info(f"Extracted {len(extracted_data.get('tests', []))} lab tests")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Lab data extraction failed: {str(e)}")
            raise RuntimeError(f"Failed to extract lab report data: {str(e)}")