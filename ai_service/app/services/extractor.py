"""
extractor.py

AI-powered extractor that converts unstructured text
(from OCR or voice) into structured JSON data.

This service uses OpenAI GPT to intelligently parse:
- Medicine names, dosages, frequencies
- Appointment dates, times, doctor names
- Lab test names, values, dates
- Patient information

UPDATES:
- user_id, doctor_id, prescription_image_url are now optional
- No validation error if optional fields are missing
- Converter handles optional parameters properly
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
    - Date and time expressions
    - Dosage formats
    - Appointment context
    """
    
    def __init__(self, api_key: str):
        """
        Initialize AI Extractor service.
        
        What happens here:
        - Create OpenAI client with provided API key
        - Initialize data converter service
        - Set up logging
        
        Parameters:
        - api_key: OpenAI API key for GPT access
        
        Called by:
        - API routes when extraction is needed
        """
        
        logger.info("Initializing AI Extractor service...")
        
        # Step 1: Create OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Step 2: Create converter instance
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
        
        UPDATED:
        - user_id, doctor_id, prescription_image_url are now OPTIONAL
        - No validation error if these fields are None
        - Converter accepts None values and handles them properly
        
        This method parses prescription text and extracts:
        - Patient name and age
        - Medicine list with dosages and frequencies
        - Doctor information
        - Date of prescription
        
        What happens here:
        1. Send raw text to GPT with specific instructions
        2. GPT analyzes and structures the data
        3. Optionally convert to backend format (even without user/doctor/image)
        4. Return structured JSON
        
        Parameters:
        - raw_text: Unstructured text from OCR (REQUIRED)
        - return_backend_format: If True, convert to backend DB format (default False)
        - user_id: User ID (OPTIONAL, can be None)
        - doctor_id: Doctor ID (OPTIONAL, can be None)
        - prescription_image_url: Image URL (OPTIONAL, can be None)
        
        Returns:
        - Structured prescription data as dict
        
        Called by:
        - API route in app/api/extract.py when user uploads prescription image
        
        Examples:
        Without backend format:
        extract_prescription_data(raw_text="Name: John...")
        
        With backend format but no user/doctor:
        extract_prescription_data(raw_text="Name: John...", return_backend_format=True)
        
        With backend format and all fields:
        extract_prescription_data(
            raw_text="Name: John...",
            return_backend_format=True,
            user_id=1,
            doctor_id=1,
            prescription_image_url="http://..."
        )
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
            # Step 1: Call GPT to extract structured data
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
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000
            )
            
            # Step 2: Get response text from GPT
            result_text = response.choices[0].message.content.strip()
            
            # Step 3: Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            elif result_text.startswith("```"):
                result_text = result_text.replace("```", "").strip()
            
            # Step 4: Parse JSON response
            extracted_data = json.loads(result_text)
            
            logger.info(f"Extracted {len(extracted_data.get('medicines', []))} medicines")
            logger.info(f"Patient: {extracted_data.get('patient_name', 'Unknown')}")
            
            # Step 5: Convert to backend format if requested
            if return_backend_format:
                logger.info("Converting to backend format...")
                
                # UPDATED: No validation - just pass whatever we have
                # user_id, doctor_id, prescription_image_url can all be None
                backend_data = self.converter.convert_prescription_to_backend(
                    ai_output=extracted_data,
                    user_id=user_id,  # Can be None
                    doctor_id=doctor_id,  # Can be None
                    prescription_image_url=prescription_image_url  # Can be None
                )
                
                return backend_data
            
            # Step 6: Return AI format (if backend format not requested)
            return extracted_data
            
        except json.JSONDecodeError as e:
            # Failed to parse JSON from GPT response
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response was: {result_text[:200]}")
            raise RuntimeError("Failed to extract structured data from prescription")
        
        except Exception as e:
            # Any other error during extraction
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
        2. Determine user intent (what they want to do)
        3. Extract relevant data based on intent
        4. Generate confirmation message
        5. Return structured response
        
        Parameters:
        - transcribed_text: Text from speech-to-text service
        
        Returns:
        - Dict containing intent, confidence, data, and confirmation
        
        Called by:
        - Voice workflow API in app/api/extract.py
        
        Example Input:
        "Add Paracetamol 500mg twice daily after food"
        
        Example Output:
        {
            "intent": "add_medicine",
            "confidence": 0.95,
            "data": {
                "medicine_name": "Paracetamol",
                "dosage": "500mg",
                "frequency": "twice daily",
                "instructions": "after food"
            },
            "confirmation_needed": true,
            "confirmation_message": "I understood: Add Paracetamol 500mg, twice daily after food. Is this correct?"
        }
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
            # Step 1: Call GPT to extract intent
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
                temperature=0.2,  # Slightly higher for natural language
                max_tokens=1000
            )
            
            # Step 2: Get response text
            result_text = response.choices[0].message.content.strip()
            
            # Step 3: Clean markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Step 4: Parse JSON
            extracted_intent = json.loads(result_text)
            
            logger.info(f"Intent: {extracted_intent.get('intent')}")
            logger.info(f"Confidence: {extracted_intent.get('confidence')}")
            
            # Step 5: Return extracted intent
            return extracted_intent
            
        except Exception as e:
            # If extraction fails, return fallback response
            logger.error(f"Intent extraction failed: {str(e)}")
            
            # Return safe fallback response
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
        - Test values
        - Units
        - Normal ranges
        - Patient information
        - Report date
        
        What happens here:
        1. Send lab report text to GPT
        2. GPT extracts all test information
        3. Identifies abnormal values
        4. Returns structured data
        
        Parameters:
        - raw_text: Unstructured lab report text from OCR
        
        Returns:
        - Dict containing structured lab test data
        
        Called by:
        - API route when user uploads lab PDF
        
        Example Input:
        "Patient: John Doe\nHemoglobin: 14.5 g/dL (Normal: 13-17)\nGlucose: 95 mg/dL"
        
        Example Output:
        {
            "patient_name": "John Doe",
            "tests": [
                {
                    "test_name": "Hemoglobin",
                    "value": "14.5",
                    "unit": "g/dL",
                    "normal_range": "13-17",
                    "status": "normal"
                }
            ]
        }
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
            # Step 1: Call GPT to extract lab data
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a lab report analyzer. Return only JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for accuracy
                max_tokens=2000
            )
            
            # Step 2: Get response text
            result_text = response.choices[0].message.content.strip()
            
            # Step 3: Clean markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            
            # Step 4: Parse JSON
            extracted_data = json.loads(result_text)
            
            logger.info(f"Extracted {len(extracted_data.get('tests', []))} lab tests")
            
            # Step 5: Return structured lab data
            return extracted_data
            
        except Exception as e:
            # Log error and raise
            logger.error(f"Lab data extraction failed: {str(e)}")
            raise RuntimeError(f"Failed to extract lab report data: {str(e)}")