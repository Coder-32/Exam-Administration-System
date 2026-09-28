import os
import re
import logging
from io import BytesIO
import PyPDF2

try:
    import pymupdf as fitz
except ImportError:
    import fitz

import pytesseract
from PIL import Image

try:
    from config import Config
except ImportError:
    from CONFIG import Config

logger = logging.getLogger(__name__)

# Configure Tesseract OCR binary path
if os.path.exists(Config.TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

def extract_personnel_from_pdf(file_bytes: bytes, role: str, use_ocr: bool = False):
    """
    Extract personnel names (teachers or staff) from an uploaded PDF file.
    
    Args:
        file_bytes: Raw bytes of the uploaded PDF file.
        role: Either 'teacher' or 'staff'.
        use_ocr: Boolean flag whether to apply Tesseract OCR on page images.
        
    Returns:
        tuple: (list_of_names, error_message)
               If successful, error_message is None.
               If failed, list_of_names is empty and error_message contains details.
    """
    if role not in ['teacher', 'staff']:
        return [], "Invalid role specified. Must be 'teacher' or 'staff'."

    text = ""
    try:
        if use_ocr:
            logger.info("Using OCR for PDF text extraction...")
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                # Render page to high-res image for OCR accuracy
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                extracted = pytesseract.image_to_string(img)
                if extracted:
                    text += extracted + "\n"
            logger.info(f"OCR successfully extracted {len(text)} characters.")
        else:
            # Native text extraction via PyPDF2
            reader = PyPDF2.PdfReader(BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            
            if len(text.strip()) < 5:
                return [], 'No text could be extracted. The PDF might be a scanned image or handwritten. Please check "Enable OCR" and try again.'

    except pytesseract.TesseractNotFoundError:
        return [], 'Tesseract OCR is not installed or not found in PATH on this server. Please install Tesseract-OCR and try again.'
    except Exception as e:
        logger.error(f"Error during PDF processing: {str(e)}")
        return [], f"PDF processing failed: {str(e)}"

    # Parse and clean extracted names
    names = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Clean up leading numbers like "1. ", "2) ", "10."
        cleaned_name = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
        # Clean OCR artifacts
        cleaned_name = re.sub(r'[^\w\s\.-]', '', cleaned_name).strip()
        
        if len(cleaned_name) > 2:
            names.append(cleaned_name)

    return names, None
