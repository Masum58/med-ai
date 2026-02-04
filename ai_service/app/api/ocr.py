"""
ocr.py (API Route)

This file defines the OCR API endpoint for the Med-AI service.

What this file does:
- Defines the /ocr/extract endpoint
- Accepts file uploads from users
- Validates uploaded files
- Calls OCRService to extract text
- Returns extracted text as JSON response

What this file does NOT do:
- Save files to disk (everything stays in memory)
- Process images directly (delegates to OCRService)
- Make business decisions about the text
- Talk directly to the database

Flow:
User uploads file → This API → OCRService → Extract text → Return JSON
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status

# Import response schema (defines JSON structure)
from app.schemas.ocr import OCRResponse

# Import OCR service (does the actual text extraction)
from app.services.ocr import OCRService

# Import OpenAI API key from config
from app.config import OPENAI_API_KEY

# Create a router for OCR-related endpoints
# This router will be registered in main.py
router = APIRouter()


@router.post(
    "/extract",  # Endpoint URL will be /ocr/extract
    response_model=OCRResponse,  # Response follows OCRResponse schema
    status_code=status.HTTP_200_OK,  # Return 200 on success
    summary="Extract text from a document using OCR",  # Shows in API docs
    description=(
        "Upload a PDF, DOCX, or IMAGE document and extract all readable text. "
        "Uses OpenAI Vision API for handwritten prescriptions and "
        "Tesseract OCR for printed documents."
    )  # Detailed description in API docs
)
async def extract_text_from_document(file: UploadFile = File(...)):
    """
    OCR extraction endpoint.
    
    This is the main endpoint that users call to extract text from documents.

    Step-by-step process:
    1. Receive the uploaded document file from user
    2. Validate that the file exists and is not empty
    3. Read file content into memory (bytes)
    4. Initialize OCR service with OpenAI API key
    5. Call OCR service to extract text
    6. Return extracted text as JSON

    Parameters:
    - file: The document file uploaded by the user
           Can be PDF, DOCX, PNG, JPG, or JPEG
           Sent as multipart/form-data

    Returns:
    - OCRResponse: JSON with extracted text
      Example: {"raw_text": "Paracetamol 500mg twice daily"}

    Errors:
    - 400 Bad Request: File is missing or empty
    - 500 Internal Server Error: OCR processing failed
    
    Called by:
    - Frontend application
    - Mobile app
    - Any client making POST request to /ocr/extract
    """

    # Step 1: Validate that a filename exists
    # file.filename will be None if no file was uploaded
    if not file.filename:
        # Return HTTP 400 error with clear message
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document file is required"
        )

    # Step 2: Read the file content into memory
    # await is needed because file.read() is async
    # This loads entire file into RAM as bytes
    file_bytes = await file.read()

    # Step 3: Ensure the uploaded file is not empty
    # Empty file would cause OCR to fail
    if not file_bytes:
        # Return HTTP 400 error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded document is empty"
        )

    try:
        # Step 4: Initialize the OCR service
        # Pass OpenAI API key so service can use Vision API
        # If OPENAI_API_KEY is None, service will only use Tesseract
        ocr_service = OCRService(openai_api_key=OPENAI_API_KEY)

        # Step 5: Extract text from the document
        # This calls the extract_text() method in OCRService
        # OCRService will:
        # - Check file type (PDF/DOCX/Image)
        # - Use appropriate extraction method
        # - Try OpenAI Vision for handwritten text
        # - Fallback to Tesseract if needed
        raw_text = ocr_service.extract_text(
            file_bytes=file_bytes,  # File content as bytes
            filename=file.filename  # Original filename
        )

        # Step 6: Return the extracted text as a structured JSON response
        # OCRResponse is a Pydantic model defined in app/schemas/ocr.py
        # It will automatically convert to JSON format
        return OCRResponse(raw_text=raw_text)

    except ValueError as error:
        # ValueError is raised for known issues:
        # - Unsupported file type (not PDF/DOCX/Image)
        # - Invalid file format
        
        # Return HTTP 400 with specific error message
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)  # Error message from OCRService
        )

    except Exception as error:
        # Catch any unexpected errors
        # This could be:
        # - OpenAI API failure
        # - Tesseract crash
        # - Memory issues
        # - Any other unexpected problem
        
        # Return HTTP 500 (server error) with safe message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from the document: {str(error)}"
        )