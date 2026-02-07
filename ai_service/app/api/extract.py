"""
extract.py (API)

AI extraction endpoints.

These endpoints convert unstructured data (OCR/voice)
into structured JSON that can be saved to database.

UPDATES:
- user_id, doctor_id, prescription_image_url are now OPTIONAL
- BackendExtractionRequest accepts None values
- Each medicine has its own before_meal and after_meal

Endpoints:
- POST /extract/prescription - Extract prescription data (AI format)
- POST /extract/prescription-backend - Extract and convert to backend format
- POST /extract/voice-intent - Extract intent from voice transcription  
- POST /extract/lab-report - Extract lab report data
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from app.schemas.extract import ExtractionRequest, ExtractionResponse
from app.services.extractor import AIExtractorService
from app.config import OPENAI_API_KEY

# Create router
router = APIRouter()


class BackendExtractionRequest(BaseModel):
    """
    Request for backend format extraction.
    
    UPDATED: All fields except raw_text are now OPTIONAL.
    
    This allows flexibility for different use cases:
    - Only OCR text available: Just send raw_text
    - Full context available: Send all fields
    """
    raw_text: str = Field(
        ..., 
        description="OCR extracted text (REQUIRED)"
    )
    user_id: Optional[int] = Field(
        default=None, 
        description="User ID from auth (OPTIONAL)"
    )
    doctor_id: Optional[int] = Field(
        default=None, 
        description="Doctor ID (OPTIONAL)"
    )
    prescription_image_url: Optional[str] = Field(
        default=None, 
        description="Uploaded image URL (OPTIONAL)"
    )


@router.post(
    "/prescription",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured data from prescription (AI format)",
    description=(
        "Send OCR text from prescription image and receive structured JSON "
        "with patient info, medicines, dosages, and frequencies in AI format."
    )
)
async def extract_prescription(request: ExtractionRequest):
    """
    Extract prescription data from OCR text in AI format.
    
    This returns AI-friendly format with text values like "twice daily".
    Use /prescription-backend for database-ready numeric format.
    
    What happens here:
    1. Validate raw text is not empty
    2. Check OpenAI API key is configured
    3. Initialize AI extractor service
    4. Extract data in AI format (text-based)
    5. Return structured response
    
    Flow:
    1. User uploads prescription image to OCR service
    2. OCR returns raw text
    3. Frontend sends text to this endpoint
    4. AI extracts structured data
    5. Return AI format (for display or further processing)
    
    Parameters:
    - request.raw_text: Unstructured OCR text
    
    Returns:
    - ExtractionResponse with AI format data
    
    Called by:
    - Testing and debugging
    - Frontend for display purposes
    - Initial extraction before backend conversion
    """
    
    # Step 1: Validate input text is not empty
    if not request.raw_text or not request.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Raw text cannot be empty"
        )
    
    # Step 2: Check OpenAI API key is configured
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI extraction service not configured"
        )
    
    try:
        # Step 3: Initialize AI extractor service
        extractor = AIExtractorService(api_key=OPENAI_API_KEY)
        
        # Step 4: Extract data in AI format (return_backend_format=False)
        extracted_data = extractor.extract_prescription_data(
            raw_text=request.raw_text,
            return_backend_format=False
        )
        
        # Step 5: Count medicines for response message
        medicine_count = len(extracted_data.get("medicines", []))
        
        # Step 6: Return structured response with AI format
        return ExtractionResponse(
            success=True,
            data=extracted_data,
            message=f"Successfully extracted {medicine_count} medicine(s)"
        )
        
    except RuntimeError as error:
        # AI extraction service error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        )
    
    except Exception as error:
        # Unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(error)}"
        )


@router.post(
    "/prescription-backend",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract and convert to backend format",
    description=(
        "Send OCR text (required) and optionally user_id, doctor_id, image_url. "
        "Returns database-ready format with numeric values and per-medicine meal timing."
    )
)
async def extract_prescription_backend(request: BackendExtractionRequest):
    """
    Extract prescription data and convert to backend database format.
    
    UPDATED:
    - Only raw_text is REQUIRED
    - user_id, doctor_id, prescription_image_url are OPTIONAL
    - Each medicine includes before_meal and after_meal
    
    This is the MAIN endpoint for prescription processing.
    
    What happens here:
    1. Validate raw text is not empty
    2. Check OpenAI API key is configured
    3. Initialize AI extractor
    4. Extract and convert to backend format
    5. Return database-ready JSON
    
    Flow:
    1. User uploads prescription image to OCR service
    2. OCR returns raw text
    3. Frontend sends text (and optionally user/doctor/image) here
    4. AI extracts and converts to backend format
    5. Frontend sends result to backend database API
    
    Parameters:
    - request.raw_text: Unstructured OCR text (REQUIRED)
    - request.user_id: Current user ID (OPTIONAL, can be None)
    - request.doctor_id: Doctor ID (OPTIONAL, can be None)
    - request.prescription_image_url: Uploaded image URL (OPTIONAL, can be None)
    
    Returns:
    - ExtractionResponse with backend-ready format
    
    Response format:
    {
        "success": true,
        "data": {
            "users": 1 or null,
            "doctor": 1 or null,
            "prescription_image": "url" or null,
            "next_appointment_date": null,
            "patient": {
                "name": "Mrs. Halima",
                "age": 45,
                "sex": null,
                "health_issues": "Diagnosis"
            },
            "medicines": [
                {
                    "name": "Paracetamol",
                    "how_many_time": 2,
                    "how_many_day": 7,
                    "stock": 14,
                    "before_meal": false,
                    "after_meal": true
                }
            ],
            "medical_tests": []
        }
    }
    
    Called by:
    - Frontend after OCR completion
    - Mobile app prescription scanner
    
    Example minimal request (only text):
    {
        "raw_text": "Name: Mrs. Halima..."
    }
    
    Example full request (all fields):
    {
        "raw_text": "Name: Mrs. Halima...",
        "user_id": 1,
        "doctor_id": 1,
        "prescription_image_url": "http://..."
    }
    """
    
    # Step 1: Validate raw_text (only required field)
    if not request.raw_text or not request.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Raw text cannot be empty"
        )
    
    # Step 2: Check OpenAI API key is configured
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI extraction service not configured"
        )
    
    try:
        # Step 3: Initialize AI extractor service
        extractor = AIExtractorService(api_key=OPENAI_API_KEY)
        
        # Step 4: Extract and convert to backend format
        # Pass optional fields (can be None)
        backend_data = extractor.extract_prescription_data(
            raw_text=request.raw_text,
            return_backend_format=True,
            user_id=request.user_id,  # Can be None
            doctor_id=request.doctor_id,  # Can be None
            prescription_image_url=request.prescription_image_url  # Can be None
        )
        
        # Step 5: Count medicines for response message
        medicine_count = len(backend_data.get("medicines", []))
        
        # Step 6: Return backend-ready format
        return ExtractionResponse(
            success=True,
            data=backend_data,
            message=f"Successfully extracted and converted {medicine_count} medicine(s)"
        )
        
    except ValueError as error:
        # Validation error from service
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )
    
    except RuntimeError as error:
        # AI extraction service error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        )
    
    except Exception as error:
        # Unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(error)}"
        )


@router.post(
    "/voice-intent",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract intent from voice transcription",
    description=(
        "Send voice transcription and receive structured intent with extracted data. "
        "Used for voice-based medicine or appointment addition."
    )
)
async def extract_voice_intent(request: ExtractionRequest):
    """
    Extract intent and data from voice input.
    
    This endpoint understands what user wants to do from their voice command.
    
    What happens here:
    1. Validate transcribed text is not empty
    2. Check OpenAI API key is configured
    3. Initialize AI extractor
    4. Extract intent and relevant data
    5. Return intent with confirmation message
    
    Flow:
    1. User speaks to STT service
    2. STT returns transcribed text
    3. Frontend sends text to this endpoint
    4. AI extracts intent and data
    5. Frontend shows confirmation to user
    6. User confirms and data is saved to database
    
    Parameters:
    - request.raw_text: Transcribed voice text from STT
    
    Returns:
    - ExtractionResponse with intent and extracted data
    
    Called by:
    - Voice workflow after speech-to-text
    - Mobile app voice commands
    
    Example Input:
    {
        "raw_text": "Add Paracetamol 500mg twice daily after food"
    }
    
    Example Output:
    {
        "success": true,
        "data": {
            "intent": "add_medicine",
            "confidence": 0.95,
            "data": {
                "medicine_name": "Paracetamol",
                "frequency": "twice daily",
                "instructions": "after food"
            },
            "confirmation_needed": true,
            "confirmation_message": "Add Paracetamol 500mg, twice daily after food. Correct?"
        }
    }
    """
    
    # Step 1: Validate transcribed text is not empty
    if not request.raw_text or not request.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcribed text cannot be empty"
        )
    
    # Step 2: Check OpenAI API key is configured
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI extraction service not configured"
        )
    
    try:
        # Step 3: Initialize AI extractor service
        extractor = AIExtractorService(api_key=OPENAI_API_KEY)
        
        # Step 4: Extract intent from voice transcription
        intent_data = extractor.extract_voice_intent(request.raw_text)
        
        
        # Step 5: Return intent response
        return ExtractionResponse(
            success=True,
            data=intent_data,
            message="Intent extracted successfully"
        )
        
    except Exception as error:
        # If extraction completely fails, return unclear intent
        # This is a safe fallback instead of error
        return ExtractionResponse(
            success=True,
            data={
                "intent": "unclear",
                "confidence": 0.0,
                "data": {"query": request.raw_text},
                "confirmation_needed": True,
                "confirmation_message": f"I heard: {request.raw_text}. What would you like me to do?"
            },
            message="Could not determine clear intent"
        )


@router.post(
    "/lab-report",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured data from lab report",
    description=(
        "Send OCR text from lab report PDF and receive structured JSON "
        "with test names, values, units, and normal ranges."
    )
)
async def extract_lab_report(request: ExtractionRequest):
    """
    Extract lab report data from OCR text.
    
    What happens here:
    1. Validate raw text is not empty
    2. Check OpenAI API key is configured
    3. Initialize AI extractor
    4. Extract all lab test data
    5. Return structured lab results
    
    Flow:
    1. User uploads lab PDF to OCR service
    2. OCR returns raw text
    3. Frontend sends text to this endpoint
    4. AI extracts test results with values and ranges
    5. Frontend sends to database
    
    Parameters:
    - request.raw_text: Unstructured lab report text from OCR
    
    Returns:
    - ExtractionResponse with lab test data
    
    Called by:
    - Frontend after lab PDF OCR
    - Mobile app lab scanner
    
    Example Output:
    {
        "success": true,
        "data": {
            "patient_name": "John Doe",
            "report_date": "2024-02-04",
            "tests": [
                {
                    "test_name": "Hemoglobin",
                    "value": "14.5",
                    "unit": "g/dL",
                    "normal_range": "13-17",
                    "status": "normal"
                }
            ],
            "significant_findings": []
        }
    }
    """
    
    # Step 1: Validate raw text is not empty
    if not request.raw_text or not request.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Raw text cannot be empty"
        )
    
    # Step 2: Check OpenAI API key is configured
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI extraction service not configured"
        )
    
    try:
        # Step 3: Initialize AI extractor service
        extractor = AIExtractorService(api_key=OPENAI_API_KEY)
        
        # Step 4: Extract lab report data
        extracted_data = extractor.extract_lab_report_data(request.raw_text)
        
        # Step 5: Count tests for response message
        test_count = len(extracted_data.get("tests", []))
        
        # Step 6: Return structured lab data
        return ExtractionResponse(
            success=True,
            data=extracted_data,
            message=f"Successfully extracted {test_count} test(s)"
        )
        
    except RuntimeError as error:
        # AI extraction service error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        )
    
    except Exception as error:
        # Unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(error)}"
        )