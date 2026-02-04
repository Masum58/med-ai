"""
converter.py

Data converter service that transforms AI extraction output
into backend database format.

This service bridges the gap between:
- AI extraction (natural language format)
- Backend database (structured numeric format)
"""

import re
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataConverterService:
    """
    DataConverterService converts AI extraction output
    to backend database format.
    
    Main responsibilities:
    - Parse frequency text to numbers ("twice daily" → 2)
    - Parse duration text to numbers ("7 days" → 7)
    - Calculate medicine stock
    - Extract meal timing (before/after)
    - Structure data for backend API
    """
    
    def __init__(self):
        """
        Initialize converter with mapping dictionaries.
        """
        
        # Frequency text to number mapping
        self.frequency_map = {
            "once daily": 1,
            "once a day": 1,
            "one time daily": 1,
            "daily": 1,
            
            "twice daily": 2,
            "twice a day": 2,
            "two times daily": 2,
            "bd": 2,  # Medical abbreviation
            
            "thrice daily": 3,
            "three times daily": 3,
            "three times a day": 3,
            "tds": 3,  # Medical abbreviation
            
            "four times daily": 4,
            "four times a day": 4,
            "qid": 4,  # Medical abbreviation
            
            "every 6 hours": 4,
            "every 8 hours": 3,
            "every 12 hours": 2
        }
        
        logger.info("Data converter initialized")
    
    def parse_frequency(self, frequency_text: str) -> int:
        """
        Convert frequency text to number.
        
        What happens here:
        1. Normalize text to lowercase
        2. Check against frequency map
        3. Try to extract number from text
        4. Return default if cannot parse
        
        Parameters:
        - frequency_text: Text like "twice daily", "3 times a day"
        
        Returns:
        - Number of times per day (integer)
        
        Examples:
        "twice daily" → 2
        "3 times daily" → 3
        "every 8 hours" → 3
        """
        
        if not frequency_text:
            logger.warning("Empty frequency text, defaulting to 1")
            return 1
        
        # Normalize text
        text = frequency_text.lower().strip()
        
        # Check direct mapping
        if text in self.frequency_map:
            result = self.frequency_map[text]
            logger.info(f"Frequency '{frequency_text}' → {result}")
            return result
        
        # Try to extract number from text
        # Pattern: "3 times daily" or "take 2 times"
        numbers = re.findall(r'\d+', text)
        if numbers:
            result = int(numbers[0])
            logger.info(f"Extracted frequency from '{frequency_text}' → {result}")
            return result
        
        # Default to 1 if cannot parse
        logger.warning(f"Could not parse frequency '{frequency_text}', defaulting to 1")
        return 1
    
    def parse_duration(self, duration_text: str) -> int:
        """
        Convert duration text to number of days.
        
        What happens here:
        1. Normalize text
        2. Extract number
        3. Convert weeks/months to days
        4. Return days as integer
        
        Parameters:
        - duration_text: Text like "7 days", "2 weeks", "1 month"
        
        Returns:
        - Number of days (integer)
        
        Examples:
        "7 days" → 7
        "2 weeks" → 14
        "1 month" → 30
        """
        
        if not duration_text:
            logger.warning("Empty duration text, defaulting to 7 days")
            return 7
        
        text = duration_text.lower().strip()
        
        # Extract number
        numbers = re.findall(r'\d+', text)
        if not numbers:
            logger.warning(f"No number in duration '{duration_text}', defaulting to 7 days")
            return 7
        
        number = int(numbers[0])
        
        # Convert based on unit
        if "week" in text:
            result = number * 7
            logger.info(f"Duration '{duration_text}' → {result} days")
            return result
        
        elif "month" in text:
            result = number * 30
            logger.info(f"Duration '{duration_text}' → {result} days")
            return result
        
        else:  # Assume days
            logger.info(f"Duration '{duration_text}' → {number} days")
            return number
    
    def parse_meal_timing(self, instructions: str) -> Dict[str, bool]:
        """
        Extract meal timing from instructions.
        
        What happens here:
        1. Check for "before" keyword
        2. Check for "after" keyword
        3. Return both flags
        
        Parameters:
        - instructions: Text like "after food", "before meals"
        
        Returns:
        - Dict with before_meal and after_meal flags
        
        Examples:
        "after food" → {"before_meal": False, "after_meal": True}
        "before meals" → {"before_meal": True, "after_meal": False}
        "with food" → {"before_meal": False, "after_meal": True}
        """
        
        if not instructions:
            return {"before_meal": False, "after_meal": False}
        
        text = instructions.lower()
        
        before_meal = any(word in text for word in ["before", "empty stomach"])
        after_meal = any(word in text for word in ["after", "with food", "with meal"])
        
        logger.info(f"Meal timing from '{instructions}' → before: {before_meal}, after: {after_meal}")
        
        return {
            "before_meal": before_meal,
            "after_meal": after_meal
        }
    
    def convert_medicine(self, medicine: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert single medicine from AI format to backend format.
        
        What happens here:
        1. Parse frequency to number
        2. Parse duration to days
        3. Calculate stock (frequency × duration)
        4. Return backend format
        
        Parameters:
        - medicine: AI extraction format
        
        Returns:
        - Backend database format
        
        AI Input:
        {
            "name": "Paracetamol",
            "frequency": "twice daily",
            "duration": "7 days"
        }
        
        Backend Output:
        {
            "name": "Paracetamol",
            "how_many_time": 2,
            "how_many_day": 7,
            "stock": 14
        }
        """
        
        # Extract fields
        name = medicine.get("name", "Unknown")
        frequency_text = medicine.get("frequency", "once daily")
        duration_text = medicine.get("duration", "7 days")
        
        # Parse to numbers
        how_many_time = self.parse_frequency(frequency_text)
        how_many_day = self.parse_duration(duration_text)
        
        # Calculate stock
        stock = how_many_time * how_many_day
        
        logger.info(f"Converted medicine: {name} → {how_many_time}x/day for {how_many_day} days = {stock} total")
        
        return {
            "name": name,
            "how_many_time": how_many_time,
            "how_many_day": how_many_day,
            "stock": stock
        }
    
    def convert_prescription_to_backend(
        self, 
        ai_output: Dict[str, Any],
        user_id: int,
        doctor_id: int,
        prescription_image_url: str
    ) -> Dict[str, Any]:
        """
        Convert complete AI extraction output to backend format.
        
        This is the main conversion function.
        
        What happens here:
        1. Extract patient info
        2. Convert all medicines
        3. Extract medical tests
        4. Parse meal timing from first medicine
        5. Structure for backend API
        
        Parameters:
        - ai_output: Complete AI extraction result
        - user_id: User ID from auth
        - doctor_id: Doctor ID from auth
        - prescription_image_url: Uploaded image URL
        
        Returns:
        - Backend API ready format
        
        Called by:
        - API endpoint after AI extraction
        """
        
        logger.info("Converting AI output to backend format...")
        
        # Extract patient info
        patient_name = ai_output.get("patient_name")
        patient_age = ai_output.get("patient_age")
        diagnosis = ai_output.get("diagnosis")
        
        # Build patient object
        patient = None
        if patient_name and patient_age:
            patient = {
                "name": patient_name,
                "age": patient_age,
                "sex": None,  # AI doesn't extract this currently
                "health_issues": diagnosis
            }
        
        # Convert medicines
        ai_medicines = ai_output.get("medicines", [])
        backend_medicines = []
        
        for med in ai_medicines:
            try:
                converted = self.convert_medicine(med)
                backend_medicines.append(converted)
            except Exception as e:
                logger.error(f"Failed to convert medicine {med.get('name')}: {e}")
                continue
        
        # Extract meal timing from first medicine with instructions
        before_meal = False
        after_meal = False
        
        for med in ai_medicines:
            instructions = med.get("instructions", "")
            if instructions:
                meal_timing = self.parse_meal_timing(instructions)
                before_meal = meal_timing["before_meal"]
                after_meal = meal_timing["after_meal"]
                break  # Use first medicine's timing
        
        # Extract medical tests
        # AI doesn't currently extract these, but backend expects them
        medical_tests = []
        
        # Build next appointment date
        # AI doesn't extract this, set to None
        next_appointment_date = None
        
        # Build final backend format
        backend_format = {
            "users": user_id,
            "doctor": doctor_id,
            "prescription_image": prescription_image_url,
            "next_appointment_date": next_appointment_date,
            "before_meal": before_meal,
            "after_meal": after_meal,
            "patient": patient,
            "medicines": backend_medicines,
            "medical_tests": medical_tests
        }
        
        logger.info(f"Conversion complete: {len(backend_medicines)} medicines converted")
        
        return backend_format
    
    def convert_voice_intent_to_medicine(
        self,
        intent_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert voice intent data to backend medicine format.
        
        Used when user adds medicine via voice.
        
        Parameters:
        - intent_data: Voice intent extraction result
        
        Returns:
        - Backend medicine format or None if not medicine intent
        
        Example:
        Voice: "Add Paracetamol 500mg twice daily for 7 days"
        
        Intent Data:
        {
            "intent": "add_medicine",
            "data": {
                "medicine_name": "Paracetamol",
                "frequency": "twice daily",
                "duration": "7 days"
            }
        }
        
        Backend Format:
        {
            "name": "Paracetamol",
            "how_many_time": 2,
            "how_many_day": 7,
            "stock": 14
        }
        """
        
        # Check if this is medicine intent
        if intent_data.get("intent") != "add_medicine":
            return None
        
        data = intent_data.get("data", {})
        
        # Build medicine object from voice data
        medicine = {
            "name": data.get("medicine_name", "Unknown"),
            "frequency": data.get("frequency", "once daily"),
            "duration": "30 days"  # Default for voice
        }
        
        # Convert to backend format
        return self.convert_medicine(medicine)