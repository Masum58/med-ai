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
- Enhanced extraction for sex/gender, next appointment
- Better parsing for #number format and meal timing
- Improved accuracy for fractional doses
- IMPROVED VOICE INTENT: Now returns database-actionable responses
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
    - Dosage formats (including fractional like 1/2 tab)
    - Appointment context
    - Patient demographics (including sex/gender)
    - Quantity formats (#60, #300, etc.)
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
        - Now extracts patient sex/gender
        - Extracts next appointment date
        - Better handling of quantity (#number) format
        - Improved meal timing and frequency detection
        
        This method parses prescription text and extracts:
        - Patient name, age, and sex/gender
        - Medicine list with dosages, frequencies, and quantities
        - Doctor information
        - Date of prescription
        - Next appointment date
        
        What happens here:
        1. Send raw text to GPT with enhanced instructions
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
        
        # IMPROVED PROMPT with better extraction instructions
        prompt = f"""You are a medical prescription parser. Extract ALL information accurately from this prescription.

Prescription Text:
{raw_text}

Extract and return ONLY valid JSON:
{{
    "patient_name": "full name (if mentioned)",
    "patient_age": age as number (if mentioned),
    "patient_sex": "Male/Female/male/female/M/F (extract from text, look for Male, Female, M, F keywords)",
    "prescription_date": "YYYY-MM-DD format (convert dates like 19-Aug-2021 or 6/8/23)",
    "doctor_name": "doctor name if mentioned",
    "next_appointment": "extract follow-up date or duration like 'after 1 month', '2 weeks', null if not mentioned",
    "medicines": [
        {{
            "name": "medicine name (clean, no Tab./Cap. prefix)",
            "type": "Tablet/Capsule/Syrup/Injection",
            "dosage": "full dosage like '10mg', '5mg', '500mg'",
            "quantity": "quantity like '1/2 tab', '1 tab', '2 tabs' - KEEP FRACTIONS AS IS, also extract #number like #60, #300",
            "frequency": "EXTRACT EXACTLY: 'once daily', 'twice daily', '3x a day', '2x a day', 'daily at bedtime', 'after breakfast & after dinner'",
            "duration": "EXTRACT FROM #NUMBER: if #60 and frequency is once daily = 60 days, if #300 and 3x daily = 100 days",
            "instructions": "FULL INSTRUCTIONS: 'at bedtime', 'after breakfast', 'after dinner', 'for muscle spasms', etc",
            "refill_needed": true/false
        }}
    ],
    "diagnosis": "diagnosis if mentioned",
    "advice": "doctor's advice"
}}

CRITICAL RULES:
1. Sex/Gender: Look for "Male", "Female", "M", "F", "male", "female" in text - IMPORTANT!
2. Next Appointment: Extract "follow up", "next visit", "after X days/weeks/months"
3. Quantity: MUST include #number format (like #60, #300) AND fractional doses (like 1/2 tab)
4. Frequency: Extract EXACTLY as written: "3x a day", "2x a day", "once daily", "daily at bedtime", "after breakfast & after dinner"
5. Duration: Calculate from #number. Example: #60 with once daily = 60 days, #300 with 3x daily = 100 days
6. Instructions: Include ALL timing info: "at bedtime", "after breakfast", "after dinner", "before meals"
7. Clean medicine names: Remove "Tab.", "Cap.", "Inj." prefixes
8. Return ONLY JSON, no explanation text
"""
        
        try:
            # Step 1: Call GPT to extract structured data with improved prompt
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical data extraction expert. Extract ALL information accurately including sex, next appointment, and #quantity numbers. Always respond in English. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.05,  # Very low temperature for maximum accuracy
                max_tokens=3000  # Increased for longer prescriptions
            )
            
            # Step 2: Get response text from GPT
            result_text = response.choices[0].message.content.strip()
            
            # Step 3: Remove markdown code blocks if present
            # Step 3: Robust JSON cleaning
            if "```" in result_text:
                parts = result_text.split("```")
                if len(parts) >= 2:
                    result_text = parts[1].strip()

            # Extract only JSON block
            start = result_text.find("{")
            end = result_text.rfind("}")
            if start != -1 and end != -1:
                result_text = result_text[start:end+1]
            
            # Step 4: Parse JSON response
            extracted_data = json.loads(result_text)
            
            logger.info(f"Extracted {len(extracted_data.get('medicines', []))} medicines")
            logger.info(f"Patient: {extracted_data.get('patient_name', 'Unknown')}, Sex: {extracted_data.get('patient_sex', 'Not extracted')}")
            logger.info(f"Next appointment: {extracted_data.get('next_appointment', 'None')}")
            
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
                
                return [
                    {
                        "id": None,  # DB will assign
                        "users": backend_data.get("users"),
                        "doctor": backend_data.get("doctor"),
                        "prescription_image": backend_data.get("prescription_image"),
                        "next_appointment_date": backend_data.get("next_appointment_date"),
                        "patient": backend_data.get("patient"),
                        "medicines": backend_data.get("medicines", []),
                        "medical_tests": backend_data.get("medical_tests", [])   
                    }
                ]
            
            # Step 6: Return AI format (if backend format not requested)
            return extracted_data
            
        except json.JSONDecodeError as e:
            # Failed to parse JSON from GPT response
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response was: {result_text[:500]}")
            raise RuntimeError("Failed to extract structured data from prescription")
        
        except Exception as e:
            # Any other error during extraction
            logger.error(f"Extraction failed: {str(e)}")
            raise RuntimeError(f"Failed to extract prescription data: {str(e)}")
    
    def extract_voice_intent(self, transcribed_text: str) -> Dict[str, Any]:
        """
        Extract intent and data from voice input.
        
        IMPROVED: Now returns database-actionable responses with API endpoints.
        
        This method understands what user wants to do from voice:
        - Add medicine
        - Schedule appointment
        - Check reminder
        - Ask question
        
        What happens here:
        1. Analyze voice transcription
        2. Determine user intent (what they want to do)
        3. Extract relevant data based on intent
        4. Provide database API endpoint and query details
        5. Return structured response with UI action
        
        Parameters:
        - transcribed_text: Text from speech-to-text service
        
        Returns:
        - Dict containing intent, database_action, ui_action, and extracted data
        
        Called by:
        - Voice workflow API in app/api/extract.py
        
        Example Input:
        "I want to know today's medicine"
        
        Example Output:
        {
            "intent": "check_reminder",
            "confidence": 0.9,
            "database_action": {
                "api_endpoint": "GET /prescriptions/my_prescriptions/",
                "method": "GET",
                "query_filters": {"today": true}
            },
            "extracted_data": {"query": "today's medicine"},
            "ui_action": "show_medicine_list",
            "user_response": "Here are today's medicines"
        }
        """
        
        logger.info("Extracting intent from voice...")
        logger.info(f"Input: {transcribed_text}")
        
        prompt = f"""Voice assistant for health management.

User: "{transcribed_text}"

Return DATABASE-ACTIONABLE JSON:

{{
    "intent": "check_reminder|add_medicine|view_prescription|schedule_appointment|refill_medicine|ask_question",
    "confidence": 0.0-1.0,
    
    "database_action": {{
        "api_endpoint": "GET /prescriptions/my_prescriptions/",
        "method": "GET|POST|PATCH",
        "query_filters": {{
            "today": true,
            "medicine_name": "name or null",
            "date_range": "today|week|month|null"
        }},
        "post_data": {{}} or null
    }},
    
    "extracted_data": {{
        "medicine_name": "name or null",
        "dosage": "dosage or null",
        "frequency": "frequency or null",
        "duration": "duration or null",
        "instructions": "instructions or null",
        "query": "user's question"
    }},
    
    "ui_action": "show_medicine_list|show_prescription_details|show_add_form|show_calendar",
    "confirmation_needed": true/false,
    "user_response": "Simple confirmation message"
}}

EXAMPLES:

"I want to know today's medicine":
{{
    "intent": "check_reminder",
    "confidence": 0.9,
    "database_action": {{
        "api_endpoint": "GET /prescriptions/my_prescriptions/",
        "method": "GET",
        "query_filters": {{"today": true}}
    }},
    "extracted_data": {{"query": "today's medicine"}},
    "ui_action": "show_medicine_list",
    "confirmation_needed": false,
    "user_response": "Here are today's medicines"
}}

"Add Paracetamol 500mg twice daily":
{{
    "intent": "add_medicine",
    "confidence": 0.9,
    "database_action": {{
        "api_endpoint": "POST /prescriptions/{{prescription_id}}/medicines/",
        "method": "POST",
        "post_data": {{"medicine_name": "Paracetamol", "dosage": "500mg", "frequency": "twice daily"}}
    }},
    "extracted_data": {{
        "medicine_name": "Paracetamol",
        "dosage": "500mg",
        "frequency": "twice daily"
    }},
    "ui_action": "show_add_form",
    "confirmation_needed": true,
    "user_response": "Adding Paracetamol 500mg twice daily. Please confirm duration and meal timing"
}}

"Show my prescriptions":
{{
    "intent": "view_prescription",
    "confidence": 0.95,
    "database_action": {{
        "api_endpoint": "GET /prescriptions/my_prescriptions/",
        "method": "GET"
    }},
    "ui_action": "show_prescription_details",
    "confirmation_needed": false,
    "user_response": "Showing your prescriptions"
}}

"I want to refill the medicine":
{{
    "intent": "refill_medicine",
    "confidence": 0.85,
    "database_action": {{
        "api_endpoint": "GET /prescriptions/my_prescriptions/",
        "method": "GET",
        "query_filters": {{"low_stock": true}}
    }},
    "extracted_data": {{
        "medicine_name": null,
        "action": "refill"
    }},
    "ui_action": "show_refill_list",
    "confirmation_needed": true,
    "user_response": "Which medicine would you like to refill? Here are your medicines with low stock"
}}

"Refill Paracetamol":
{{
    "intent": "refill_medicine",
    "confidence": 0.9,
    "database_action": {{
        "api_endpoint": "PATCH /prescriptions/{{prescription_id}}/medicines/{{medicine_id}}/",
        "method": "PATCH",
        "post_data": {{"action": "refill"}}
    }},
    "extracted_data": {{
        "medicine_name": "Paracetamol",
        "action": "refill"
    }},
    "ui_action": "show_refill_confirmation",
    "confirmation_needed": true,
    "user_response": "Refilling Paracetamol. How many days supply do you need?"
}}

Return ONLY JSON.
"""
        
        try:
            # Step 1: Call GPT to extract intent
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content":(
                            "You are a professional voice assistant for a health system. "
                            "ALWAYS generate responses in English only. "
                            "Do NOT switch language even if the user speaks another language. "
                            "Return only valid JSON with database-actionable responses."
                        ) 
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # deterministic intent detection
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
            logger.info(f"Database Action: {extracted_intent.get('database_action', {}).get('api_endpoint')}")
            
            # Step 5: Return extracted intent
            return extracted_intent
            
        except Exception as e:
            # If extraction fails, return fallback response
            logger.error(f"Intent extraction failed: {str(e)}")
            
            # Return safe fallback response
            return {
                "intent": "unclear",
                "confidence": 0.0,
                "database_action": None,
                "extracted_data": {"query": transcribed_text},
                "ui_action": "show_error",
                "confirmation_needed": True,
                "user_response": f"I'm not sure what you would like to do. Could you please clarify?"
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

    def generate_general_response(self, user_text: str) -> str:
        """
        Handle non-medical / general conversation safely.
        Production-safe general AI fallback.
        """

        logger.info("Generating general AI response...")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional AI assistant. "
                            "ALWAYS respond in English only. "
                            "Do NOT switch to any other language even if the user speaks another language. "
                            "If the user asks medical database related questions, "
                            "tell them to use the health features. "
                            "Otherwise answer naturally and helpfully."
                        )
                    },
                    {
                        "role": "user",
                        "content": user_text
                    }
                ],
                temperature=0.6,
                max_tokens=800
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"General AI response failed: {str(e)}")
            return "I'm here to help. Could you please clarify your question?"
