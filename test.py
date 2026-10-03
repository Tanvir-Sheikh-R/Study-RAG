from __future__ import annotations
import torch
import torchvision.transforms.functional as F
import json
from pathlib import Path
import torch
import torchvision.transforms.functional as F
import easyocr
from pypdf import PdfReader
from pdf2image import convert_from_path
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

PROJECT_ROOT = Path.cwd().parent 

TOC_KEYWORDS = ("সূচিপত্র", "সুচিপত্র", "বিষয়সূচি")
DEFAULT_MATCH_THRESHOLD = 80
POOPLER_PATH = r"C:\poppler\Library\bin"


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
    separators=["\n\n\n", "\n\n", "\n", "।", " ", ""],
)

with open(r"D:\AI-ML\AI Projects\Study RAG\chapters.json", "r", encoding="utf-8") as file:
        INDEX_INFOS = json.load(file)



def get_page_metadatas(class_num, subject, page):
    metas = {}
    if class_num is None or subject is None or page is None or page < 0:
        return metas

    book_section = INDEX_INFOS.get("all_books", {}).get(class_num, {}).get(subject)
    if not book_section:
        return metas

    for chapter in book_section:
        start = chapter.get("starting_page")
        if start is None or start > page:
            continue

        if chapter.get("sub_chapters"):
            for sub in chapter["sub_chapters"]:
                sub_start = sub.get("starting_page")
                if sub_start is not None and sub_start <= page:
                    metas["part"] = chapter.get("chapter_name")
                    metas["chapter"] = sub.get("sub_chapter_name")
                    if sub.get("writer_name"):
                        metas["writer_name"] = sub.get("writer_name")
                    else:
                        metas.pop("writer_name", None)
        else:
            metas["chapter"] = chapter.get("chapter_name")
            metas.pop("part", None)
            metas.pop("writer_name", None)

    return metas


READER = easyocr.Reader(['bn', 'en'], gpu=torch.cuda.is_available())

def ocr_pdf_to_pages_gpu(pdf_path: Path, poppler_path=POOPLER_PATH):
    class_number = pdf_path.parent.name.lower()
    sub_name = pdf_path.stem.lower()

    # Broadened keywords list to handle potential mixed characters
    keywords = ("সূচিপত্র", "সুচিপত্র", "বিষয়সূচি", "CONTENTS", "contents")
    tracker = False
    page_num = 0

    page_count = len(PdfReader(str(pdf_path)).pages)
    print(f"Total Pages to Process: {page_count}")
    
    # 1. Convert PDF to PIL Images (CPU-bound poppler task)
    images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
    pages = []

    # Check if GPU is ready
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    for i, img in tqdm(enumerate(images, start=1), total=len(images), desc=f"Processing images via {device}"):
        
        # 2. Move image to GPU VRAM using PyTorch
        img_tensor = F.to_tensor(img).to(device)  # Normalizes to [0.0, 1.0], Shape: [C, H, W]
        
        # 3. GPU Preprocessing: Convert to Grayscale ('L')
        if img_tensor.shape[0] == 3:  # If RGB
            img_tensor = 0.2989 * img_tensor[0] + 0.5870 * img_tensor[1] + 0.1140 * img_tensor[2]
            img_tensor = img_tensor.unsqueeze(0)  # Shape: [1, H, W]

        # 4. GPU Preprocessing: Autocontrast (Normalize min/max scale)
        min_val, max_val = img_tensor.min(), img_tensor.max()
        if max_val > min_val:
            img_tensor = (img_tensor - min_val) / (max_val - min_val)

        # 5. Convert Tensor back to NumPy uint8 array expected by EasyOCR 
        img_numpy = (img_tensor.squeeze(0).cpu().numpy() * 255).astype('uint8')

        # 6. Run GPU-based OCR Inference
        # paragraph=True merges bounding boxes together into natural text strings
        results = READER.readtext(img_numpy, paragraph=True)
        text = "\n".join([res[1] for res in results])

        # Check for table of contents keywords
        if any(k in text for k in keywords):
            tracker = True

        if tracker:
            pages.append({"page_number": page_num, "page_content": text, "book_name": sub_name, "class_number": class_number})
            page_num += 1
        else:
            pages.append({"page_number": 0, "page_content": text, "book_name": sub_name, "class_number": class_number})

    return pages

#  -->-*************************** For all books (Use it when add new books) ***********************

# main_path = r"D:\AI-ML\AI Projects\Study RAG\pdf"

# all_book_pages = {}
# for class_name in os.listdir(main_path):
#     for pdf in os.listdir(os.path.join(main_path, class_name)):
#         if pdf.endswith(".pdf"):
#             key = f"{class_name}_{pdf}"
#             all_book_pages[key] = ocr_pdf_to_pages_gpu(Path(os.path.join(main_path, class_name, pdf)))

# book_dicts = [page for pages in all_book_pages.values() for page in pages]

#  -->-*************************** For all books (Use it when add new books) ***********************

single_path = r"D:\AI-ML\AI Projects\Study RAG\pdf\Class_9_10\General\Math.pdf"

single_book = ocr_pdf_to_pages_gpu(Path(single_path))

documents = []
for item in tqdm(single_book, desc="Processing PDF pages"):
    content = item.pop("page_content", "")

    class_num = item.get("class_number")
    subject = item.get("book_name")
    page = item.get("page_number")

    if page is None or page < 0:
        continue  # pre-TOC / cover pages — not indexed

    metas = get_page_metadatas(class_num, subject, page)
    if not metas:
        print(f"⚠️ No metadata found for page {page}")

    doc = Document(page_content=content, metadata=item | metas)
    documents.append(doc)

    print(f"Book {item['book_name']}, Class {item['class_number']}, Done --")


with open('output_document.txt', 'w', encoding='utf-8') as file:
    for doc in documents:
        file.write(json.dumps({"page_content": doc.page_content, "metadata": doc.metadata}, ensure_ascii=False) + "\n")

print(f"{len(documents)} page-level documents")