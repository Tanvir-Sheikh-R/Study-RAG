import os
import pytesseract
from pdf2image import convert_from_path
from PIL import ImageOps
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter


class_no : int = 5
subject_name : str = "Bangla"
chapter_no : int = None

pdf_path = os.path.join("pdf", f"Class_{class_no}", f"{subject_name}.pdf")

poppler_path = r"C:\poppler\Library\bin"  # adjust to your install

output_dir = os.path.join("extracted_text", f"Class_{class_no}")
os.makedirs(output_dir, exist_ok=True)



text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
        separators=["\n\n", "\n", "।", " ", ""],
    )



def pdf_to_text_file(pdf_path):

    pages = convert_from_path(pdf_path, dpi=400, poppler_path=poppler_path)

    full_text = []
    for i, page in enumerate(tqdm(pages, desc="OCR Processing...")):
        # Preprocess: grayscale + contrast boost (helps Bangla conjuncts a lot)
        img = page.convert('L')
        img = ImageOps.autocontrast(img)

        text = pytesseract.image_to_string(img, lang='ben')


# svgd..............





        full_text.append(f"[PAGE_{i-4}]\n{text}")

        print(f"--- Page {i+1}/{len(pages)} done ---")

    # Save as one combined text file
    output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(pdf_path))[0]}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))

    print("Done. Saved to", output_path)



def text_to_chunks(pdf_path):
    with open(pdf_path, "r", encoding="utf-8") as f:
        text = f.read()
    chunks  = text_splitter.create_documents(texts = [text], metadatas= {})
    return chunks 



pdf_to_text_file(pdf_path)
text_file_path = os.path.join(output_dir, f"{subject_name}.txt")
documents = text_to_chunks(text_file_path)
print(f"Total chunks created: {len(documents)}")