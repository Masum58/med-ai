"""
ocr.py

This file is used to read uploaded documents or images
and extract readable text from them.

Supported file types:
- PDF (normal PDF and scanned PDF)
- DOCX (Word files)
- PNG / JPG / JPEG (image files)

Uses multiple extraction methods:
1. OpenAI Vision API (best for handwritten prescriptions)
2. Tesseract OCR (fallback for printed text)

This file:
- Only returns extracted text
- Does NOT save files anywhere
- Does NOT contain FastAPI routes
- Does NOT talk to the database or backend
"""

import io
import base64
from typing import List, Optional

import cv2
import numpy as np
from openai import OpenAI

import fitz  # Used to read PDF files (PyMuPDF)
from docx import Document  # Used to read Word (DOCX) files
from PIL import Image  # Used for image handling
import pytesseract  # OCR engine to read text from images

# Set Tesseract executable path for Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class OCRService:
    """
    OCRService is responsible for one job only:
    reading documents or images and extracting text from them.
    
    This class can use two methods:
    1. OpenAI Vision API - for handwritten text (best accuracy)
    2. Tesseract OCR - for printed text (free, offline)
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize OCR service.
        
        What happens here:
        - Store OpenAI API key if provided
        - Create OpenAI client for Vision API calls
        
        Parameters:
        - openai_api_key: Optional OpenAI API key for Vision API
        """
        
        # Store OpenAI client (will be None if no key provided)
        self.openai_client = None
        
        # If API key is provided, create OpenAI client
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)

    def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """
        Main entry point used by the application.
        
        This function decides which extraction method to use
        based on the file type.

        What happens here:
        1. Check file extension
        2. Call appropriate extraction method
        3. Return extracted text

        Parameters:
        - file_bytes: uploaded file data (kept in memory)
        - filename: original file name

        Returns:
        - extracted text as a single string
        
        Called by:
        - API route in app/api/ocr.py
        """

        # Make filename lowercase to avoid case issues
        filename = filename.lower()

        # If the file is a PDF, extract text from PDF
        if filename.endswith(".pdf"):
            # Call PDF extraction method below
            return self._extract_from_pdf(file_bytes)

        # If the file is a DOCX, extract text from DOCX
        if filename.endswith(".docx"):
            # Call DOCX extraction method below
            return self._extract_from_docx(file_bytes)

        # If the file is an image, extract text using OCR
        if filename.endswith((".png", ".jpg", ".jpeg")):
            # Call image extraction method below
            return self._extract_from_image(file_bytes)

        # Any other file type is not supported
        raise ValueError(
            "Unsupported file type. Only PDF, DOCX, PNG, JPG, and JPEG are allowed."
        )

    def _extract_with_openai_vision(self, file_bytes: bytes) -> Optional[str]:
        """
        Extract text using OpenAI Vision API.
        
        This is the BEST method for handwritten prescriptions.
        
        What happens here:
        1. Convert image to base64 format
        2. Send to OpenAI Vision API
        3. Get extracted text back
        4. Return the text
        
        Why this is better than Tesseract:
        - Understands handwriting
        - Knows medical terminology
        - Can guess unclear words from context
        
        Parameters:
        - file_bytes: image file data
        
        Returns:
        - extracted text or None if API call fails
        
        Called by:
        - _extract_from_image() method
        - _extract_from_pdf() method (for scanned PDFs)
        """
        
        # If no OpenAI client, return None
        if not self.openai_client:
            return None
        
        try:
            # Step 1: Convert image bytes to base64 string
            # OpenAI API needs base64 format
            base64_image = base64.b64encode(file_bytes).decode('utf-8')
            
            # Step 2: Call OpenAI Vision API
            # Model: gpt-4o (latest vision model)
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                # Detailed prompt telling AI what to extract
                                "text": """Extract ALL text from this medical prescription/document. 
                                Include:
                                - Patient name and age
                                - All medication names
                                - Dosages and frequencies
                                - Doctor's instructions
                                - Any lab test names
                                - Dates and appointments
                                
                                Return ONLY the extracted text, preserving the structure.
                                If text is unclear, make your best guess but mark with [?]."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    # Send base64 image to API
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000  # Maximum response length
            )
            
            # Step 3: Extract text from API response
            extracted_text = response.choices[0].message.content
            
            # Step 4: Return cleaned text
            return extracted_text.strip()
            
        except Exception as e:
            # If API call fails, print error and return None
            # The calling function will try Tesseract as fallback
            print(f"OpenAI Vision API failed: {str(e)}")
            return None

    def _preprocess_for_handwritten(self, image: Image.Image) -> Image.Image:
        """
        Special preprocessing for handwritten text.
        
        This method prepares images specifically for handwritten content.
        It's different from regular preprocessing because handwriting
        needs gentler processing to preserve strokes.
        
        What happens here:
        1. Resize image to larger size
        2. Convert to grayscale
        3. Enhance contrast
        4. Gentle noise removal
        5. Apply automatic thresholding
        
        Parameters:
        - image: PIL Image object
        
        Returns:
        - processed PIL Image ready for OCR
        
        Called by:
        - _extract_from_image() method
        """
        
        # Step 1: Convert PIL Image to numpy array for OpenCV
        img_array = np.array(image)
        
        # Step 2: Resize image if too small
        # Bigger images = better OCR accuracy
        height, width = img_array.shape[:2]
        if width < 1500:
            # Calculate scale factor to make width 1500px
            scale = 1500 / width
            new_width = 1500
            new_height = int(height * scale)
            
            # Resize using high-quality LANCZOS interpolation
            # This preserves handwriting details
            img_array = cv2.resize(
                img_array, 
                (new_width, new_height), 
                interpolation=cv2.INTER_LANCZOS4
            )
        
        # Step 3: Convert to grayscale if colored
        if len(img_array.shape) == 3:
            # Image has 3 channels (RGB), convert to 1 channel (grayscale)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            # Already grayscale
            gray = img_array
        
        # Step 4: Enhance contrast using CLAHE
        # CLAHE = Contrast Limited Adaptive Histogram Equalization
        # Makes dark text darker and light background lighter
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Step 5: Gentle denoising that preserves handwriting strokes
        # h=10 is gentle denoising strength
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
        
        # Step 6: Otsu's automatic thresholding
        # Automatically finds best threshold to separate text from background
        _, binary = cv2.threshold(
            denoised, 
            0,  # Threshold value (0 = auto)
            255,  # Max value (white)
            cv2.THRESH_BINARY + cv2.THRESH_OTSU  # Otsu's method
        )
        
        # Step 7: Check if image is inverted (dark background, light text)
        # If average brightness < 127, image is mostly dark
        if np.mean(binary) < 127:
            # Invert colors: black becomes white, white becomes black
            binary = cv2.bitwise_not(binary)
        
        # Step 8: Convert back to PIL Image format
        return Image.fromarray(binary)

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Standard preprocessing for printed text.
        
        This method is more aggressive than handwritten preprocessing.
        It's optimized for clean, printed documents.
        
        What happens here:
        1. Resize if too small
        2. Convert to grayscale
        3. Auto-rotate if tilted
        4. Increase contrast
        5. Remove noise
        6. Apply thresholding
        7. Morphological operations
        8. Sharpen text
        
        Parameters:
        - image: PIL Image object
        
        Returns:
        - processed PIL Image ready for OCR
        
        Called by:
        - _extract_from_image() method
        - _extract_from_pdf() method
        """
        
        # Step 1: Convert PIL Image to numpy array
        img_array = np.array(image)
        
        # Step 2: Resize if image is too small
        height, width = img_array.shape[:2]
        if width < 1000:
            # Calculate scale to make width 1000px
            scale = 1000 / width
            new_width = 1000
            new_height = int(height * scale)
            
            # Resize using cubic interpolation
            img_array = cv2.resize(
                img_array, 
                (new_width, new_height), 
                interpolation=cv2.INTER_CUBIC
            )
        
        # Step 3: Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Step 4: Automatic rotation correction (deskewing)
        # Find all non-white pixels
        coords = np.column_stack(np.where(gray > 0))
        
        if len(coords) > 0:
            # Find minimum area rectangle containing all text
            # This gives us the rotation angle
            angle = cv2.minAreaRect(coords)[-1]
            
            # Adjust angle to correct range
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            # Only rotate if angle is significant (> 0.5 degrees)
            if abs(angle) > 0.5:
                # Calculate rotation matrix
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                
                # Apply rotation
                gray = cv2.warpAffine(
                    gray, 
                    M, 
                    (w, h), 
                    flags=cv2.INTER_CUBIC, 
                    borderMode=cv2.BORDER_REPLICATE
                )
        
        # Step 5: Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast_enhanced = clahe.apply(gray)
        
        # Step 6: Remove noise using bilateral filter
        # This filter removes noise while preserving edges
        denoised = cv2.bilateralFilter(contrast_enhanced, 9, 75, 75)
        
        # Step 7: Apply adaptive thresholding
        # Makes text black and background white
        thresh = cv2.adaptiveThreshold(
            denoised,
            255,  # Max value
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # Method
            cv2.THRESH_BINARY,  # Type
            15,  # Block size
            10  # Constant subtracted
        )
        
        # Step 8: Morphological closing to fill small holes in text
        kernel = np.ones((2, 2), np.uint8)
        morph = cv2.morphologyEx(
            thresh, 
            cv2.MORPH_CLOSE,  # Closing operation
            kernel, 
            iterations=1
        )
        
        # Step 9: Sharpen the text
        kernel_sharpen = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])
        sharpened = cv2.filter2D(morph, -1, kernel_sharpen)
        
        # Step 10: Convert back to PIL Image
        processed_image = Image.fromarray(sharpened)
        
        return processed_image

    def _extract_from_docx(self, file_bytes: bytes) -> str:
        """
        Extract text from a DOCX (Word) file.

        DOCX files already contain text, so OCR is not needed.
        We just read paragraphs directly.
        
        What happens here:
        1. Load DOCX from memory
        2. Read all paragraphs
        3. Combine into single text
        
        Parameters:
        - file_bytes: DOCX file data
        
        Returns:
        - extracted text
        
        Called by:
        - extract_text() method when file is .docx
        """

        # Step 1: Load DOCX from memory (not from disk)
        document = Document(io.BytesIO(file_bytes))

        # Step 2: Create list to store paragraphs
        paragraphs: List[str] = []

        # Step 3: Loop through all paragraphs in document
        for paragraph in document.paragraphs:
            # Get paragraph text and remove extra spaces
            text = paragraph.text.strip()
            
            # Only add non-empty paragraphs
            if text:
                paragraphs.append(text)

        # Step 4: Combine all paragraphs with newlines
        return "\n".join(paragraphs)

    def _extract_from_pdf(self, file_bytes: bytes) -> str:
        """
        Extract text from a PDF file.

        What happens here:
        1. Try to extract text directly (for normal PDFs)
        2. If no text found, it's a scanned PDF
        3. Convert pages to images
        4. Try OpenAI Vision API first
        5. Fallback to Tesseract OCR if needed
        
        Parameters:
        - file_bytes: PDF file data
        
        Returns:
        - extracted text from all pages
        
        Called by:
        - extract_text() method when file is .pdf
        """

        # Step 1: Open PDF from memory
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        
        # Step 2: Create list to store text from all pages
        extracted_pages: List[str] = []

        # Step 3: Process each page one by one
        for page_index in range(len(pdf_document)):
            # Get current page
            page = pdf_document[page_index]

            # Step 4: Try to get text directly from PDF
            page_text = page.get_text().strip()

            # Step 5: If text exists, add it to results
            if page_text:
                extracted_pages.append(page_text)
                continue  # Move to next page

            # Step 6: No text found - this is a scanned PDF
            # Convert page to image with high DPI for better quality
            pixmap = page.get_pixmap(dpi=300)  # 300 DPI = high quality
            image_bytes = pixmap.tobytes()
            
            # Step 7: Try OpenAI Vision first if available
            if self.openai_client:
                # Call OpenAI Vision API (defined above)
                vision_text = self._extract_with_openai_vision(image_bytes)
                
                if vision_text:
                    # Vision API succeeded, add text and move to next page
                    extracted_pages.append(vision_text)
                    continue
            
            # Step 8: OpenAI Vision failed or not available
            # Fallback to Tesseract OCR
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Run Tesseract OCR with standard config
            custom_config = r'--oem 3 --psm 6'
            ocr_text = pytesseract.image_to_string(
                processed_image, 
                config=custom_config
            ).strip()

            # Add OCR result if not empty
            if ocr_text:
                extracted_pages.append(ocr_text)

        # Step 9: Combine all pages with double newlines
        return "\n\n".join(extracted_pages)

    def _extract_from_image(self, file_bytes: bytes) -> str:
        """
        Extract text from an image file (PNG, JPG, JPEG).

        This is the main method for prescription images.
        
        Extraction priority:
        1. OpenAI Vision API (best for handwritten)
        2. Tesseract with preprocessing (fallback)
        
        What happens here:
        1. Try OpenAI Vision first
        2. If that fails, try Tesseract with standard preprocessing
        3. If that fails, try Tesseract with handwritten preprocessing
        4. Return best result
        
        Parameters:
        - file_bytes: image file data
        
        Returns:
        - extracted text
        
        Called by:
        - extract_text() method when file is image
        """
        
        # Strategy 1: Try OpenAI Vision first (best for handwritten)
        if self.openai_client:
            # Call OpenAI Vision API (defined above)
            vision_text = self._extract_with_openai_vision(file_bytes)
            
            # If Vision API returned good result (more than 20 characters)
            if vision_text and len(vision_text.strip()) > 20:
                return vision_text
        
        # Strategy 2: OpenAI failed or not available - use Tesseract
        
        # Load image from memory
        image = Image.open(io.BytesIO(file_bytes))
        
        # Create list to store different OCR attempts
        results = []
        
        # Try 1: Standard preprocessing (for printed text)
        try:
            # Preprocess image (defined above)
            processed_standard = self._preprocess_image(image)
            
            # Try multiple PSM modes (defined below)
            text1 = self._ocr_with_multiple_psm(processed_standard)
            
            if text1.strip():
                results.append(text1)
        except:
            # If preprocessing fails, continue to next method
            pass
        
        # Try 2: Handwritten preprocessing (for handwritten text)
        try:
            # Preprocess for handwriting (defined above)
            processed_handwritten = self._preprocess_for_handwritten(image)
            
            # Try multiple PSM modes
            text2 = self._ocr_with_multiple_psm(processed_handwritten)
            
            if text2.strip():
                results.append(text2)
        except:
            # If preprocessing fails, continue
            pass
        
        # Return the longest result (usually most accurate)
        if results:
            return max(results, key=len)
        
        # Last resort: direct OCR without any preprocessing
        return pytesseract.image_to_string(image).strip()

    def _ocr_with_multiple_psm(self, processed_image: Image.Image) -> str:
        """
        Try multiple PSM (Page Segmentation Mode) settings.
        
        PSM modes tell Tesseract how to interpret the page:
        - PSM 3: Fully automatic page segmentation
        - PSM 6: Uniform block of text
        - PSM 11: Sparse text (good for handwritten)
        - PSM 4: Single column of text
        
        What happens here:
        1. Try each PSM mode
        2. Calculate confidence score for each
        3. Return result with highest confidence
        
        Parameters:
        - processed_image: preprocessed PIL Image
        
        Returns:
        - extracted text with best confidence
        
        Called by:
        - _extract_from_image() method
        """
        
        # Track best result
        best_text = ""
        max_confidence = 0
        
        # PSM modes to try
        psm_modes = [3, 6, 11, 4]
        
        # Try each PSM mode
        for psm in psm_modes:
            try:
                # Create Tesseract config string
                custom_config = f'--oem 3 --psm {psm}'
                
                # Run OCR
                text = pytesseract.image_to_string(
                    processed_image, 
                    config=custom_config
                )
                
                # Get detailed data including confidence scores
                data = pytesseract.image_to_data(
                    processed_image, 
                    config=custom_config, 
                    output_type=pytesseract.Output.DICT
                )
                
                # Extract confidence values (filter out -1 which means no data)
                confidences = [
                    int(conf) for conf in data['conf'] 
                    if conf != '-1'
                ]
                
                # Calculate average confidence
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Keep result if it has better confidence
                if avg_confidence > max_confidence and text.strip():
                    max_confidence = avg_confidence
                    best_text = text
                    
            except:
                # If this PSM mode fails, try next one
                continue
        
        # Return best result
        return best_text.strip()