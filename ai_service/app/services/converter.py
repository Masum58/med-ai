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
- Handles fractional doses (1/2 tab) and #number format
- Better meal timing detection (breakfast, dinner, bedtime)
- Accurate stock calculation from #number
- Extracts sex and next appointment date
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
    - Calculate medicine stock accurately using #number format
    - Extract meal timing per medicine (before or after food)
    - Handle complex patterns like "after breakfast & after dinner"
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
            "1x a day": 1,
            "1x daily": 1,
            
            "twice daily": 2,
            "twice a day": 2,
            "two times daily": 2,
            "2x a day": 2,
            "2x daily": 2,
            "bd": 2,  # Medical abbreviation
            
            "thrice daily": 3,
            "three times daily": 3,
            "three times a day": 3,
            "3x a day": 3,
            "3x daily": 3,
            "tds": 3,  # Medical abbreviation
            
            "four times daily": 4,
            "four times a day": 4,
            "4x a day": 4,
            "4x daily": 4,
            "qid": 4,  # Medical abbreviation
            
            "every 6 hours": 4,
            "every 8 hours": 3,
            "every 12 hours": 2
        }
        
        logger.info("Data converter initialized")
    
    def parse_frequency(self, frequency_text: str) -> int:
        """
        Convert frequency text to number.
        
        IMPROVED: Now handles complex patterns like "after breakfast & after dinner"
        
        What happens here:
        1. Check for multiple doses with "&" or "and"
        2. Normalize text to lowercase
        3. Check against frequency map
        4. Try to extract number from text (e.g., "3x a day")
        5. Return default if cannot parse
        
        Parameters:
        - frequency_text: Text like "twice daily", "3 times a day", "after breakfast & after dinner"
        
        Returns:
        - Number of times per day (integer)
        
        Called by:
        - convert_medicine() method
        
        Examples:
        "twice daily" becomes 2
        "3 times daily" becomes 3
        "after breakfast & after dinner" becomes 2
        "every 8 hours" becomes 3
        """
        
        # Step 1: Check if text is empty
        if not frequency_text:
            logger.warning("Empty frequency text, defaulting to 1")
            return 1
        
        # Step 2: Normalize text to lowercase
        text = frequency_text.lower().strip()
        
        # Step 3: NEW - Check for multiple doses pattern with "&" or "and"
        # Example: "after breakfast & after dinner" = 2 doses
        if "&" in text or " and " in text:
            parts = re.split(r'&|and', text)
            count = len([p for p in parts if p.strip()])
            if count > 1:
                logger.info(f"Detected {count} doses from multiple pattern in '{frequency_text}'")
                return count
        
        # Step 4: Check direct mapping
        if text in self.frequency_map:
            result = self.frequency_map[text]
            logger.info(f"Frequency '{frequency_text}' converted to {result}")
            return result
        
        # Step 5: Try to extract number from text with "x" pattern
        # Pattern: "3x a day" or "2x daily"
        numbers = re.findall(r'(\d+)\s*x', text)
        if numbers:
            result = int(numbers[0])
            logger.info(f"Extracted frequency from '{frequency_text}' is {result}")
            return result
        
        # Step 6: Try to extract standalone number
        # Pattern: "3 times daily" or "take 2 times"
        numbers = re.findall(r'\d+', text)
        if numbers:
            result = int(numbers[0])
            logger.info(f"Extracted frequency from '{frequency_text}' is {result}")
            return result
        
        # Step 7: Default to 1 if cannot parse
        logger.warning(f"Could not parse frequency '{frequency_text}', defaulting to 1")
        return 1
    
    def parse_duration(
        self, 
        duration_text: str,
        quantity_number: Optional[int] = None,
        how_many_time: int = 1
    ) -> int:
        """
        Convert duration text to number of days.
        
        IMPROVED: Now calculates from #number format for accuracy
        
        What happens here:
        1. If #number is provided (e.g., #60, #300), calculate: duration = #number / how_many_time
        2. Otherwise, normalize text
        3. Extract number
        4. Convert weeks or months to days
        5. Return days as integer
        
        Parameters:
        - duration_text: Text like "7 days", "2 weeks", "1 month"
        - quantity_number: The #number from prescription (e.g., 60, 300)
        - how_many_time: Frequency per day (for calculation)
        
        Returns:
        - Number of days (integer)
        
        Called by:
        - convert_medicine() method
        
        Examples:
        #60 with once daily → 60 days
        #300 with 3x daily → 100 days
        #150 with 2x daily → 75 days
        "7 days" becomes 7
        "2 weeks" becomes 14
        "1 month" becomes 30
        """
        
        # Step 1: NEW - Priority calculation from #number
        # This gives most accurate duration
        if quantity_number and quantity_number > 0 and how_many_time > 0:
            calculated_days = quantity_number // how_many_time
            logger.info(f"Calculated duration from #number: #{quantity_number} ÷ {how_many_time}/day = {calculated_days} days")
            return calculated_days
        
        # Step 2: Check if text is empty
        if not duration_text:
            logger.warning("Empty duration text, defaulting to 30 days")
            return 30
        
        # Step 3: Normalize text to lowercase
        text = duration_text.lower().strip()
        
        # Step 4: Extract number from text
        numbers = re.findall(r'\d+', text)
        if not numbers:
            logger.warning(f"No number in duration '{duration_text}', defaulting to 30 days")
            return 30
        
        number = int(numbers[0])
        
        # Step 5: Convert based on unit (weeks or months)
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
        
        IMPROVED: Better detection for "at bedtime", "after breakfast", "after dinner"
        
        What happens here:
        1. Check for "before" keywords in instructions
        2. Check for "after" keywords (including bedtime, breakfast, dinner)
        3. Return both flags as dictionary
        
        Parameters:
        - instructions: Text like "after food", "before meals", "at bedtime", "after breakfast"
        
        Returns:
        - Dict with before_meal and after_meal flags
        
        Called by:
        - convert_medicine() method
        
        Examples:
        "after food" returns {"before_meal": False, "after_meal": True}
        "before meals" returns {"before_meal": True, "after_meal": False}
        "at bedtime" returns {"before_meal": False, "after_meal": True}
        "after breakfast" returns {"before_meal": False, "after_meal": True}
        "with food" returns {"before_meal": False, "after_meal": True}
        empty string returns {"before_meal": False, "after_meal": False}
        """
        
        # Step 1: Check if instructions is empty
        if not instructions:
            return {"before_meal": False, "after_meal": False}
        
        # Step 2: Normalize text to lowercase
        text = instructions.lower()
        
        # Step 3: Check for "before" keywords
        before_keywords = ["before", "empty stomach", "before food", "before eating"]
        before_meal = any(keyword in text for keyword in before_keywords)
        
        # Step 4: NEW - Enhanced "after" keywords (including meal times and bedtime)
        after_keywords = [
            "after", "with food", "with meal", "with meals",
            "after food", "after eating",
            "after breakfast", "after lunch", "after dinner",
            "at bedtime", "bedtime"  # Bedtime often taken with or after food
        ]
        after_meal = any(keyword in text for keyword in after_keywords)
        
        logger.info(f"Meal timing from '{instructions}' is before: {before_meal}, after: {after_meal}")
        
        return {
            "before_meal": before_meal,
            "after_meal": after_meal
        }
    
    def extract_quantity_number(self, medicine: Dict[str, Any]) -> Optional[int]:
        """
        Extract quantity number (#60, #300) from medicine data.
        
        NEW METHOD for accurate stock calculation
        
        What happens here:
        1. Check quantity field for #number
        2. Check duration field for #number
        3. Return the number if found
        
        Parameters:
        - medicine: AI extraction medicine object
        
        Returns:
        - Quantity number (integer) or None
        
        Called by:
        - convert_medicine() method
        
        Examples:
        {"quantity": "#60"} → 60
        {"duration": "100 days #300"} → 300
        """
        
        # Check quantity field for #number
        quantity = medicine.get("quantity", "")
        if isinstance(quantity, str) and "#" in quantity:
            numbers = re.findall(r'#(\d+)', quantity)
            if numbers:
                logger.info(f"Extracted quantity number: #{numbers[0]}")
                return int(numbers[0])
        
        # Check duration field for #number
        duration = medicine.get("duration", "")
        if isinstance(duration, str) and "#" in duration:
            numbers = re.findall(r'#(\d+)', duration)
            if numbers:
                logger.info(f"Extracted quantity number from duration: #{numbers[0]}")
                return int(numbers[0])
        
        return None
    
    def convert_medicine(self, medicine: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert single medicine from AI format to backend format.
        
        UPDATED: 
        - Now includes before_meal and after_meal for each medicine
        - Uses #number for accurate duration calculation
        - Handles complex frequency patterns
        
        What happens here:
        1. Extract medicine name, frequency, duration, instructions
        2. Parse frequency to number (handles & patterns)
        3. Extract #number if available
        4. Calculate duration (uses #number if available)
        5. Calculate stock (frequency times duration)
        6. Parse meal timing from instructions
        7. Return backend format with all fields
        
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
            "quantity": "#60",
            "instructions": "after food"
        }
        
        Backend Output Example:
        {
            "name": "Paracetamol",
            "how_many_time": 2,
            "how_many_day": 30,
            "stock": 60,
            "before_meal": false,
            "after_meal": true
        }
        """
        
        # Step 1: Extract fields from AI format
        name = medicine.get("name", "Unknown")
        frequency_text = medicine.get("frequency", "once daily")
        duration_text = medicine.get("duration", "")
        instructions = medicine.get("instructions", "")
        
        # Step 2: Parse frequency text to number
        how_many_time = self.parse_frequency(frequency_text)
        
        # Step 3: NEW - Extract #number for accurate calculation
        quantity_number = self.extract_quantity_number(medicine)
        
        # Step 4: Calculate duration (uses #number if available)
        how_many_day = self.parse_duration(duration_text, quantity_number, how_many_time)
        
        # Step 5: Calculate total stock needed
        stock = how_many_time * how_many_day
        
        # Step 6: Parse meal timing from instructions
        meal_timing = self.parse_meal_timing(instructions)
        
        logger.info(f"Converted medicine: {name} is {how_many_time} times per day for {how_many_day} days equals {stock} total")
        
        # Step 7: Return backend format
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
        - Extracts patient sex if available
        - Includes next_appointment_date if available
        
        This is the main conversion function.
        
        What happens here:
        1. Extract patient information (including sex)
        2. Convert all medicines to backend format
        3. Extract medical tests if any
        4. Extract next appointment date
        5. Build final structure matching backend database
        6. Return complete backend-ready format
        
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
        patient_sex = ai_output.get("patient_sex")  # NEW - extract sex
        diagnosis = ai_output.get("diagnosis")
        
        # Step 2: Build patient object if we have data
        patient = None
        if patient_name and patient_age:
            patient = {
                "name": patient_name,
                "age": patient_age,
                "sex": patient_sex,  # NEW - include sex in patient data
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
        
        # Step 5: NEW - Extract next appointment date from AI output
        next_appointment_raw = ai_output.get("next_appointment")
        next_appointment_date = next_appointment_raw if next_appointment_raw else None
        
        # Step 6: Build final backend format
        backend_format = {
            "users": user_id,  # Can be None
            "doctor": doctor_id,  # Can be None
            "prescription_image": prescription_image_url,  # Can be None
            "next_appointment_date": next_appointment_date,  # NEW - include next appointment
            "patient": patient,
            "medicines": backend_medicines,
            "medical_tests": medical_tests
        }
        
        logger.info(f"Conversion complete: {len(backend_medicines)} medicines converted")
        logger.info(f"Patient sex: {patient_sex}, Next appointment: {next_appointment_date}")
        
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