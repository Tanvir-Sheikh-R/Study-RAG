"""pipeline/ocr.py — Stage 1: OCR + TOC page classification + disk cache."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from pipeline.settings.config import Config


log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Disk-cache helpers
# --------------------------------------------------------------------------- #

def _read_cache(path: Path) -> list[dict] | None:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _write_cache(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# TOC classification (shared by both OCR engines)
# --------------------------------------------------------------------------- #

def _classify_by_toc(
    raw_pages: list[str],
    class_number: str,
    book_name: str,
    toc_keywords: tuple[str, ...] = Config.TOC_KEYWORDS,
) -> list[dict]:
    """Mark pre-TOC pages as page_number=-1, content pages as 0-based index."""
    pages = []
    found_toc = False
    page_num = 0

    for text in raw_pages:
        if not found_toc and any(k in text for k in toc_keywords):
            found_toc = True

        pages.append({
            "page_number": page_num if found_toc else -1,
            "page_content": text,
            "book_name": book_name,
            "class_number": class_number,
        })
        if found_toc:
            page_num += 1

    return pages


# --------------------------------------------------------------------------- #
# OCR engines
# --------------------------------------------------------------------------- #

def ocr_cpu(pdf_path: Path, poppler_path: str = Config.POPPLER_PATH) -> list[dict]:
    """Tesseract OCR — CPU only, no heavy GPU deps required."""
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import ImageOps
    from pypdf import PdfReader
    from tqdm import tqdm

    book_name = pdf_path.stem.lower()
    class_number = pdf_path.parent.name.lower()
    page_count = len(PdfReader(str(pdf_path)).pages)
    log.info("CPU OCR: %s — %d pages", pdf_path.name, page_count)

    images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
    texts = []
    for img in tqdm(images, desc=f"Tesseract · {pdf_path.name}"):
        img = ImageOps.autocontrast(img.convert("L"))
        texts.append(pytesseract.image_to_string(img, lang=Config.TESSERACT_LANG))

    return _classify_by_toc(texts, class_number, book_name)


def ocr_gpu(pdf_path: Path, poppler_path: str = Config.POPPLER_PATH) -> list[dict]:
    """EasyOCR — GPU accelerated (falls back to CPU if no CUDA)."""
    import torch
    import torchvision.transforms.functional as TF
    import easyocr
    from pdf2image import convert_from_path
    from pypdf import PdfReader
    from tqdm import tqdm

    book_name = pdf_path.stem.lower()
    class_number = pdf_path.parent.name.lower()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    page_count = len(PdfReader(str(pdf_path)).pages)
    log.info("GPU OCR (%s): %s — %d pages", device, pdf_path.name, page_count)

    reader = easyocr.Reader(["bn", "en"], gpu=device.type == "cuda")
    images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)

    texts = []
    for img in tqdm(images, desc=f"EasyOCR/{device} · {pdf_path.name}"):
        tensor = TF.to_tensor(img).to(device)

        # RGB → grayscale
        if tensor.shape[0] == 3:
            tensor = (0.2989 * tensor[0] + 0.5870 * tensor[1] + 0.1140 * tensor[2]).unsqueeze(0)

        # Autocontrast
        lo, hi = tensor.min(), tensor.max()
        if hi > lo:
            tensor = (tensor - lo) / (hi - lo)

        arr = (tensor.squeeze(0).cpu().numpy() * 255).astype("uint8")
        results = reader.readtext(arr, paragraph=True)
        texts.append("\n".join(r[1] for r in results))

    return _classify_by_toc(texts, class_number, book_name)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

ENGINES = {"cpu": ocr_cpu, "gpu": ocr_gpu}


def run_ocr(pdf_path: Path, engine: str = "cpu", force: bool = False) -> list[dict]:
    """OCR a PDF, using a JSON cache to avoid re-processing on reruns."""
    book_id = pdf_path.stem.lower()
    cache_path = Config.OCR_CACHE_DIR / f"{book_id}.json"

    if not force:
        cached = _read_cache(cache_path)
        if cached is not None:
            log.info("OCR cache hit: %s", book_id)
            return cached

    pages = ENGINES[engine](pdf_path)
    _write_cache(cache_path, pages)
    return pages
