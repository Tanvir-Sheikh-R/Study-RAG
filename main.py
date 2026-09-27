import pytesseract
from pdf2image import convert_from_path
from PIL import ImageOps
import os
from tqdm import tqdm

pdf_path = r"pdf\Class 10\Secondary (BV)-2026_Class 9-10_Career_compressed.pdf"
poppler_path = r"C:\poppler\Library\bin"  # adjust to your install
output_dir = "extracted_text"
os.makedirs(output_dir, exist_ok=True)

# Convert all pages to images
pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)

full_text = []

for i, page in enumerate(tqdm(pages, desc="OCR Processing...")):
    # Preprocess: grayscale + contrast boost (helps Bangla conjuncts a lot)
    img = page.convert('L')
    img = ImageOps.autocontrast(img)

    text = pytesseract.image_to_string(img, lang='ben')
    full_text.append(text)

    print(f"--- Page {i+1}/{len(pages)} done ---")

# Save as one combined text file
with open(os.path.join(output_dir, "book_full.txt"), "w", encoding="utf-8") as f:
    f.write("\n\n".join(full_text))

print("Done. Saved to", os.path.join(output_dir, "book_full.txt"))