import pytesseract
from pdf2image import convert_from_path

path = r"pdf\Class 5\1. BGS Class Five_2025_outline_ (29-09-25)-2_compressed.pdf"
pages = convert_from_path(path, dpi=300, poppler_path=r"C:\poppler\Library\bin", )
for i, page in enumerate(pages):
    text = pytesseract.image_to_string(page)
    print(f"--- Page {i+1} ---\n{text}")