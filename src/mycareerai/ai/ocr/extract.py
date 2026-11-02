"""Reads text from a PDF, using OCR only for pages without a usable text layer."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pypdfium2
import pytesseract

# Fewer characters than this means the page is a scan, or a text layer with nothing useful in it.
MIN_TEXT_LAYER_CHARS = 50
OCR_DPI = 300
PDF_POINTS_PER_INCH = 72
# OCR takes seconds per page, and the render needs memory in proportion to the page area.
MAX_PAGES = 5
MAX_PAGE_POINTS = 20 * PDF_POINTS_PER_INCH


class OcrError(Exception):
    """A document could not be read. The message is safe to show to the user."""


@dataclass(frozen=True)
class Page:
    number: int
    text: str
    method: Literal["text_layer", "ocr"]


@dataclass(frozen=True)
class ExtractedDocument:
    pages: tuple[Page, ...]

    @property
    def text(self) -> str:
        return "\n".join(page.text for page in self.pages if page.text)

    @property
    def method(self) -> str:
        methods = {page.method for page in self.pages}
        if len(methods) > 1:
            return "mixed"
        return "ocr" if methods == {"ocr"} else "pdf_text_layer"

# -------------------------------------- HELPERS -----------------------------------------------------------

def _normalise(text: str) -> str:
    lines = (re.sub(r"[ \t\f]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _ocr_page(page: pypdfium2.PdfPage) -> str:
    image = page.render(scale=OCR_DPI / PDF_POINTS_PER_INCH).to_pil()
    try:
        text = pytesseract.image_to_string(image, config="--psm 1")
    except pytesseract.TesseractNotFoundError as err:
        raise OcrError("Tesseract is not installed. Install it with `brew install tesseract`.") from err
    # Tesseract tends to read the gap after a bullet as a vertical bar.
    return re.sub(r"(?m)^\s*-\s*\|\s*", "- ", _normalise(text))

# ------------------------------------- FUNCTIONS-----------------------------------------------------------

def extract_text(path: Path, force_ocr: bool = False) -> ExtractedDocument:
    try:
        document = pypdfium2.PdfDocument(path)
    except (pypdfium2.PdfiumError, OSError) as err:
        raise OcrError(f"{path.name} could not be opened as a PDF.") from err

    pages = []
    try:
        if len(document) > MAX_PAGES:
            raise OcrError(f"{path.name} has more than {MAX_PAGES} pages. Upload a shorter CV.")
        for index in range(len(document)):
            page = document[index]
            text = _normalise(page.get_textpage().get_text_bounded())
            if force_ocr or len(text) < MIN_TEXT_LAYER_CHARS:
                if max(page.get_size()) > MAX_PAGE_POINTS:
                    raise OcrError(f"Page {index + 1} of {path.name} is too large to read.")
                pages.append(Page(index + 1, _ocr_page(page), "ocr"))
            else:
                pages.append(Page(index + 1, text, "text_layer"))
    finally:
        document.close()

    extracted = ExtractedDocument(tuple(pages))
    if not extracted.text:
        raise OcrError(f"No text was found in {path.name}.")
    return extracted
