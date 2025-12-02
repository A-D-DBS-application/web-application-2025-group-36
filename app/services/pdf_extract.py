# app/services/pdf_extract.py
from pypdf import PdfReader
import os


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text from a PDF using pypdf (modern + reliable).
    Returns a string containing all text from all pages.
    """

    if not os.path.exists(pdf_path):
        print(f"❌ FILE NOT FOUND: {pdf_path}")
        return ""

    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        print(f"❌ Failed to open PDF with pypdf: {e}")
        return ""

    extracted_text = []

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            extracted_text.append(text)
        except Exception as e:
            print(f"⚠️ Could not extract text from page {i}: {e}")
            continue

    full_text = "\n".join(extracted_text).strip()

    if len(full_text) < 30:
        print("⚠️ WARNING: Extracted PDF text seems very short.")

    return full_text
