import os
import fitz
from app.services.doc_ingestion import _read_pdf, preprocess_legal_text, parse_legal_units

def test_pdf_extraction(path):
    print(f"Testing extraction for: {path}")
    if not os.path.exists(path):
        print("File not found.")
        return

    try:
        text = _read_pdf(path)
        print(f"Extracted text length: {len(text)}")
        if len(text) < 100:
            print(f"Text preview: {text!r}")
        else:
            print(f"Text preview (first 100 chars): {text[:100]!r}")
        
        cleaned = preprocess_legal_text(text)
        print(f"Cleaned text length: {len(cleaned)}")
        
        units = parse_legal_units(text)
        print(f"Parsed units: {len(units)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test with the known existing PDF
    test_pdf_extraction("e:\\Hackathons\\AIU1\\NyaySaathi\\constitution_of_india.pdf")
