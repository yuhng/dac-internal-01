import shutil
from pathlib import Path

import pypdfium2
import pytest

from mycareerai.ai.ocr import OcrError, build_record, extract_text
from mycareerai.ai.ocr import extract as extract_module

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
SAMPLE_CVS = sorted(DATA_DIR.glob("*.pdf"))

needs_sample = pytest.mark.skipif(not SAMPLE_CVS, reason="no sample PDF in data/")
needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")


@pytest.fixture
def blank_pdf(tmp_path):
    path = tmp_path / "scan.pdf"
    document = pypdfium2.PdfDocument.new()
    document.new_page(612, 792)
    document.save(path)
    document.close()
    return path


def test_uses_ocr_for_a_page_without_a_text_layer(blank_pdf, monkeypatch):
    monkeypatch.setattr(extract_module.pytesseract, "image_to_string", lambda *a, **k: "- | Scanned text\n")
    document = extract_text(blank_pdf)
    assert document.method == "ocr"
    assert document.text == "- Scanned text"


def test_rejects_a_document_with_no_text(blank_pdf, monkeypatch):
    monkeypatch.setattr(extract_module.pytesseract, "image_to_string", lambda *a, **k: "  \n")
    with pytest.raises(OcrError, match="No text"):
        extract_text(blank_pdf)


def test_rejects_a_file_that_is_not_a_pdf(tmp_path):
    path = tmp_path / "notes.pdf"
    path.write_text("not a pdf")
    with pytest.raises(OcrError, match="could not be opened"):
        extract_text(path)


def test_reports_missing_tesseract(blank_pdf, monkeypatch):
    def not_installed(*args, **kwargs):
        raise extract_module.pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(extract_module.pytesseract, "image_to_string", not_installed)
    with pytest.raises(OcrError, match="Tesseract is not installed"):
        extract_text(blank_pdf)


@needs_sample
def test_sample_cv_uses_the_text_layer_and_matches_the_schema():
    record = build_record(SAMPLE_CVS[0])
    assert record["collection_method"] == "pdf_text_layer"
    assert record["review_status"] == "pending"
    assert record["work_experience"] and record["education"] and record["certifications"]
    assert record["responsibilities"] is None


@needs_sample
def test_same_file_gets_the_same_id():
    assert build_record(SAMPLE_CVS[0])["id"] == build_record(SAMPLE_CVS[0])["id"]


@needs_sample
@needs_tesseract
def test_ocr_finds_the_same_structure_as_the_text_layer():
    native = build_record(SAMPLE_CVS[0])
    ocr = build_record(SAMPLE_CVS[0], force_ocr=True)
    assert ocr["collection_method"] == "ocr"
    keys = ("title", "company", "start_date", "end_date")
    assert [[r[k] for k in keys] for r in ocr["work_experience"]] == [[r[k] for k in keys] for r in native["work_experience"]]
    assert ocr["education"] == native["education"]
    assert ocr["certifications"] == native["certifications"]
