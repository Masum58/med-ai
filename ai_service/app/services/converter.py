"""
converter.py

Data converter service that transforms AI extraction output
into backend database format.

This service bridges the gap between:
- AI extraction (natural language format)
- Backend database (structured numeric format)

UPDATES:
- Meal timing now added to each individual medicine
- user_id, doctor_id, prescription_image_url are now optional
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
    - Parse frequency text to numbers ("twice daily" to 2)
    - Parse duration text to numbers ("7 days" to 7)
    - Calculate medicine stock
    - Extract meal timing per medicine (before or after food)
    - Structure data for backend API
    """
    
    def __init__(self):
        """
        Initialize converter with mapping dictionaries.
        
        What happens here:
        - Create frequency mapping dictionary
        - Set up logging
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
        
        Called by:
        - convert_medicine() method
        
        Examples:
        "twice daily" becomes 2
        "3 times daily" becomes 3
        "every 8 hours" becomes 3
        """
        
        # Step 1: Check if text is empty
        if not frequency_text:
            logger.warning("Empty frequency text, defaulting to 1")
            return 1
        
        # Step 2: Normalize text to lowercase
        text = frequency_text.lower().strip()
        
        # Step 3: Check direct mapping
        if text in self.frequency_map:
            result = self.frequency_map[text]
            logger.info(f"Frequency '{frequency_text}' converted to {result}")
            return result
        
        # Step 4: Try to extract number from text
        # Pattern: "3 times daily" or "take 2 times"
        numbers = re.findall(r'\d+', text)
        if numbers:
            result = int(numbers[0])
            logger.info(f"Extracted frequency from '{frequency_text}' is {result}")
            return result
        
        # Step 5: Default to 1 if cannot parse
        logger.warning(f"Could not parse frequency '{frequency_text}', defaulting to 1")
        return 1
    
    def parse_duration(self, duration_text: str) -> int:
        """
        Convert duration text to number of days.
        
        What happens here:
        1. Normalize text
        2. Extract number
        3. Convert weeks or months to days
        4. Return days as integer
        
        Parameters:
        - duration_text: Text like "7 days", "2 weeks", "1 month"
        
        Returns:
        - Number of days (integer)
        
        Called by:
        - convert_medicine() method
        
        Examples:
        "7 days" becomes 7
        "2 weeks" becomes 14
        "1 month" becomes 30
        """
        
        # Step 1: Check if text is empty
        if not duration_text:
            logger.warning("Empty duration text, defaulting to 7 days")
            return 7
        
        # Step 2: Normalize text to lowercase
        text = duration_text.lower().strip()
        
        # Step 3: Extract number from text
        numbers = re.findall(r'\d+', text)
        if not numbers:
            logger.warning(f"No number in duration '{duration_text}', defaulting to 7 days")
            return 7
        
        number = int(numbers[0])
        
        # Step 4: Convert based on unit (weeks or months)
        if "week" in text:
            result = number * 7
            logger.info(f"Duration '{duration_text}' converted to {result} days")
            return result
        
        elif "month" in text:
            result = number * 30
            logger.info(f"Duration '{duration_text}' converted to {result} days")
            return result
        
        else:  # Assume days if no unit specified
            logger.info(f"Duration '{duration_text}' is {number} days")
            return number
    
    def parse_meal_timing(self, instructions: str) -> Dict[str, bool]:
        """
        Extract meal timing from instructions.
        
        What happens here:
        1. Check for "before" keyword in instructions
        2. Check for "after" keyword in instructions
        3. Return both flags as dictionary
        
        Parameters:
        - instructions: Text like "after food", "before meals"
        
        Returns:
        - Dict with before_meal and after_meal flags
        
        Called by:
        - convert_medicine() method
        
        Examples:
        "after food" returns {"before_meal": False, "after_meal": True}
        "before meals" returns {"before_meal": True, "after_meal": False}
        "with food" returns {"before_meal": False, "after_meal": True}
        empty string returns {"before_meal": False, "after_meal": False}
        """
        
        # Step 1: Check if instructions is empty
        if not instructions:
            return {"before_meal": False, "after_meal": False}
        
        # Step 2: Normalize text to lowercase
        text = instructions.lower()
        
        # Step 3: Check for "before" keywords
        before_meal = any(word in text for word in ["before", "empty stomach"])
        
        # Step 4: Check for "after" keywords
        after_meal = any(word in text for word in ["after", "with food", "with meal"])
        
        logger.info(f"Meal timing from '{instructions}' is before: {before_meal}, after: {after_meal}")
        
        return {
            "before_meal": before_meal,
            "after_meal": after_meal
        }
    
    def convert_medicine(self, medicine: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert single medicine from AI format to backend format.
        
        UPDATED: Now includes before_meal and after_meal for each medicine.
        
        What happens here:
        1. Extract medicine name, frequency, duration, instructions
        2. Parse frequency to number
        3. Parse duration to number of days
        4. Calculate stock (frequency times duration)
        5. Parse meal timing from instructions
        6. Return backend format with all fields
        
        Parameters:
        - medicine: AI extraction format
        
        Returns:
        - Backend database format
        
        Called by:
        - convert_prescription_to_backend() method
        
        AI Input Example:
        {
            "name": "Paracetamol",
            "frequency": "twice daily",
            "duration": "7 days",
            "instructions": "after food"
        }
        
        Backend Output Example:
        {
            "name": "Paracetamol",
            "how_many_time": 2,
            "how_many_day": 7,
            "stock": 14,
            "before_meal": false,
            "after_meal": true
        }
        """
        
        # Step 1: Extract fields from AI format
        name = medicine.get("name", "Unknown")
        frequency_text = medicine.get("frequency", "once daily")
        duration_text = medicine.get("duration", "7 days")
        instructions = medicine.get("instructions", "")
        
        # Step 2: Parse frequency text to number
        how_many_time = self.parse_frequency(frequency_text)
        
        # Step 3: Parse duration text to number of days
        how_many_day = self.parse_duration(duration_text)
        
        # Step 4: Calculate total stock needed
        stock = how_many_time * how_many_day
        
        # Step 5: Parse meal timing from instructions
        meal_timing = self.parse_meal_timing(instructions)
        
        logger.info(f"Converted medicine: {name} is {how_many_time} times per day for {how_many_day} days equals {stock} total")
        
        # Step 6: Return backend format
        return {
            "name": name,
            "how_many_time": how_many_time,
            "how_many_day": how_many_day,
            "stock": stock,
            "before_meal": meal_timing["before_meal"],
            "after_meal": meal_timing["after_meal"]
        }
    
    def convert_prescription_to_backend(
        self, 
        ai_output: Dict[str, Any],
        user_id: Optional[int] = None,
        doctor_id: Optional[int] = None,
        prescription_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert complete AI extraction output to backend format.
        
        UPDATED:
        - user_id, doctor_id, prescription_image_url are now OPTIONAL
        - Meal timing removed from global level
        - Each medicine now has its own before_meal and after_meal
        
        This is the main conversion function.
        
        What happens here:
        1. Extract patient information
        2. Convert all medicines to backend format
        3. Extract medical tests if any
        4. Build final structure matching backend database
        5. Return complete backend-ready format
        
        Parameters:
        - ai_output: Complete AI extraction result
        - user_id: User ID from auth (optional, can be None)
        - doctor_id: Doctor ID from auth (optional, can be None)
        - prescription_image_url: Uploaded image URL (optional, can be None)
        
        Returns:
        - Backend API ready format
        
        Called by:
        - API endpoint after AI extraction (app/api/extract.py)
        """
        
        logger.info("Converting AI output to backend format...")
        
        # Step 1: Extract patient information from AI output
        patient_name = ai_output.get("patient_name")
        patient_age = ai_output.get("patient_age")
        diagnosis = ai_output.get("diagnosis")
        
        # Step 2: Build patient object if we have data
        patient = None
        if patient_name and patient_age:
            patient = {
                "name": patient_name,
                "age": patient_age,
                "sex": None,  # AI does not extract gender currently
                "health_issues": diagnosis
            }
        
        # Step 3: Convert all medicines from AI format to backend format
        ai_medicines = ai_output.get("medicines", [])
        backend_medicines = []
        
        for med in ai_medicines:
            try:
                # Convert each medicine
                converted = self.convert_medicine(med)
                backend_medicines.append(converted)
            except Exception as e:
                # Log error but continue with other medicines
                logger.error(f"Failed to convert medicine {med.get('name')}: {e}")
                continue
        
        # Step 4: Extract medical tests (currently not extracted by AI)
        medical_tests = []
        
        # Step 5: Build next appointment date (currently not extracted by AI)
        next_appointment_date = None
        
        # Step 6: Build final backend format
        backend_format = {
            "users": user_id,  # Can be None
            "doctor": doctor_id,  # Can be None
            "prescription_image": prescription_image_url,  # Can be None
            "next_appointment_date": next_appointment_date,
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
        
        Used when user adds medicine via voice command.
        
        What happens here:
        1. Check if intent is add_medicine
        2. Extract medicine data from intent
        3. Build medicine object
        4. Convert using convert_medicine() method
        5. Return backend format
        
        Parameters:
        - intent_data: Voice intent extraction result
        
        Returns:
        - Backend medicine format or None if not medicine intent
        
        Called by:
        - Voice workflow API when user speaks medicine command
        
        Example:
        User says: "Add Paracetamol 500mg twice daily for 7 days"
        
        Intent Data:
        {
            "intent": "add_medicine",
            "data": {
                "medicine_name": "Paracetamol",
                "frequency": "twice daily",
                "instructions": "after food"
            }
        }
        
        Backend Format Output:
        {
            "name": "Paracetamol",
            "how_many_time": 2,
            "how_many_day": 30,
            "stock": 60,
            "before_meal": false,
            "after_meal": true
        }
        """
        
        # Step 1: Check if this is medicine intent
        if intent_data.get("intent") != "add_medicine":
            return None
        
        # Step 2: Extract medicine data from intent
        data = intent_data.get("data", {})
        
        # Step 3: Build medicine object from voice data
        medicine = {
            "name": data.get("medicine_name", "Unknown"),
            "frequency": data.get("frequency", "once daily"),
            "duration": "30 days",  # Default duration for voice
            "instructions": data.get("instructions", "")
        }
        
        # Step 4: Convert to backend format using convert_medicine()
        return self.convert_medicine(medicine)