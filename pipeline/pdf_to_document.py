import os
import pytesseract
from pdf2image import convert_from_path
from PIL import ImageOps
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter


class_no : int = None
subject_name : str = None
chapter_no : int = None

pdf_path = f"pdf\{class_no}\{subject_name}.pdf"

poppler_path = r"C:\poppler\Library\bin"  # adjust to your install

output_dir = f"extracted_text\{class_no}"
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


        text_splitter.create_documents(texts = [text], metadatas= {"page": f"PAGE_{i-4}", "chapter_number": chapter_no})
# svgd..............





        full_text.append(f"[PAGE_{i-4}]\n{text}")

        print(f"--- Page {i+1}/{len(pages)} done ---")

    # Save as one combined text file
    with open(os.path.join(output_dir, f"{pdf_path[4:-4]}.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))

    print("Done. Saved to", os.path.join(output_dir, f"{pdf_path[4:-4]}.txt"))



def text_to_chunks(pdf_path):
    with open(os.path.join(output_dir, pdf_path), "r", encoding="utf-8") as f:
        text = f.read()
    chunks  = text_splitter.create_documents(texts = [text], metadatas= {})
    return chunks 



documents = text_to_chunks("book_full.txt")