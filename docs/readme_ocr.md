# OCR module

Turns a resume PDF into one row matching `data/schema.yaml`, including sections compatible with the improvement loader.

Code: `src/mycareerai/module/ocr/`  
Tests: `tests/module/ocr/`

Despite the name, the module only uses OCR when it has to. It reads a PDF's text layer first, because that is exact, while OCR can misread characters. Only pages with no usable text go to Tesseract.

## Setup

Install the Python dependencies:

```sh
uv sync
```

OCR also needs Tesseract, which is a system program and not a Python package:

```sh
brew install tesseract
```

Text-based PDFs work without Tesseract. It is only needed for scanned pages or `--force-ocr`.

## Usage

Run these commands from the repo root.

Print the row to the terminal:

```sh
uv run python -m mycareerai.module.ocr "data/resume.pdf"
```

Write the row to a file. The folder must already exist:

```sh
mkdir -p data/processed
uv run python -m mycareerai.module.ocr "data/resume.pdf" --output data/processed/row.json
```

| Option | Default | Purpose |
| --- | --- | --- |
| `--output PATH` | Print to the terminal | File to write. An existing file is overwritten |
| `--source TEXT` | The PDF's file name | Value for the `source` column |
| `--license TEXT` | `unknown` | Value for the `license` column |
| `--force-ocr` | Off | Use OCR on every page, even if a text layer exists |

From Python:

```python
from pathlib import Path

from mycareerai.module.ocr import OcrError, build_record

try:
    row = build_record(Path("data/resume.pdf"), source="upload", license="user-provided")
except OcrError as err:
    print(err)
```

## How it works

```text
PDF
 │
 ▼
extract.py    Read each page: text layer, or OCR if the page has too little text
 │
 ▼
resume.py     Split the text into sections and parse each one with rules
 │
 ▼
record.py     Build the row and validate it against data/schema.yaml
 │
 ▼
__main__.py   Print the row or write it to a file
```

### 1. Extract text (`extract.py`)

Each page is handled separately, so a PDF can mix digital and scanned pages.

1. Read the page's text layer with `pypdfium2`.
2. If it has at least 50 characters (`MIN_TEXT_LAYER_CHARS`), use it.
3. Otherwise, render the page at 300 DPI (`OCR_DPI`) and run Tesseract on the image.
4. Tidy the text by collapsing repeated spaces and removing blank lines. On OCR pages, also fix bullets misread as `- |`.

`collection_method` records which route was used:

| Value | Meaning |
| --- | --- |
| `pdf_text_layer` | Every page used the text layer |
| `ocr` | Every page used OCR |
| `mixed` | Some pages used each |

### 2. Parse the resume (`resume.py`)

Parsing uses rules, not a model. It splits the text at known headings such as `WORK EXPERIENCE`, `EDUCATION` and `SKILLS`, then parses each section:

| Section | Rule |
| --- | --- |
| Experience | A non-bullet line ending in a date range starts a new role. Later bullets become its `description` |
| Education | Finds a degree such as `BSc` or `Diploma`, then takes the institution, field and year around it |
| Skills | Splits comma-separated lists. `Python (Pandas, Polars)` becomes three skills |
| Certifications | Reads a certifications section, or a `Certification:` line inside Skills |
| Contact details | Takes the first email address and the first run of 8 to 15 digits that is not a year range, anywhere in the text |

Two role header styles are supported:

```text
Company | Job Title  Jun 2024 – Present
Job Title, Company (2023 – Present)
```

`hard_skills` combines the Skills section with terms from `module/terms/hard_skills.yaml` found anywhere in the document. `soft_skills` comes from `module/terms/soft_skills.yaml`. `skills` is both combined, without duplicates. An alias is stored under its term's `name`, so `Postgres` and `PostgreSQL` can't count as two skills if both are listed.

### 3. Build the row (`record.py`)

`build_record` assembles the existing 24 fields plus `document_id`, `metadata` and `sections`, then validates the row against `data/schema.yaml`. An invalid row raises `jsonschema.ValidationError` instead of being returned.

### Improvement document adapter (`adapter.py`)

The CLI and document API include the section representation automatically. `document_id` equals the existing file-hash `id`; `metadata` carries `collection_method` and `review_status`.

Each section has a deterministic `section_id`, a `section_name` and its original `content`, including headings, bullets and line breaks. Summary, experience and skills map to `professional_summary`, `work_experience` and `technical_skills`; projects, education and certifications retain their names. Repeated sections remain separate. Text before any recognized heading, or a document without recognized headings, becomes `unclassified`. Unknown headings within a section remain in that section's content.

Sections use `content` rather than parsed role entries, so unfamiliar role layouts cannot discard evidence. Skills content comes from the actual skills section, not the terms detected elsewhere in the CV. The full `text` and existing parsed fields remain available to scoring and database ingestion. The JSONB document row stores the new fields without a database migration.

For an older OCR record, call `to_improvement_document(record)` from `mycareerai.module.ocr` to obtain just the improvement document representation. Section IDs are deterministic for the same document text and order; they are not edit locations across revised CVs. Document versioning and scoring-to-improvement orchestration are separate work.

| Column | Value |
| --- | --- |
| `id` | SHA-256 of the file, so the same file always gets the same id |
| `document_type` | Always `resume` |
| `text` | The full extracted text |
| `email`, `phone` | First match in the text, as written. `null` if none was found |
| `work_experience`, `education`, `certifications`, `skills`, `hard_skills`, `soft_skills` | Parsed values. Empty list if nothing was found |
| `responsibilities`, `requirements`, `qualifications` | `null`, as these apply to job descriptions |
| `occupation`, `seniority_level`, `industry`, `resume_format`, `writing_style` | `null`, as these need a model or reviewer |
| `source` | `--source`, or the file name |
| `collection_method` | `pdf_text_layer`, `ocr` or `mixed` |
| `license` | `--license`, or `unknown` |
| `annotation_method` | `rule_based` |
| `review_status` | `pending` |

## Errors

The CLI prints `OcrError` messages and exits with status 1.

| Message | Cause |
| --- | --- |
| `<file> could not be opened as a PDF.` | The file is missing, damaged, or not a PDF |
| `<file> has more than 5 pages...` | The PDF has more than `MAX_PAGES` pages |
| `Page <n> of <file> is too large to read.` | A page that needs OCR is wider or taller than 20 inches |
| `No text was found in <file>.` | No text layer, and OCR found nothing |
| `Tesseract is not installed...` | A page needed OCR and Tesseract is missing |

## Limitations

- **Resumes only:** job descriptions are not parsed.
- **PDFs only:** DOCX and image files are not supported.
- **Layouts:** parsing is fitted to the heading and role styles above. Other layouts can produce empty or wrong structured fields, even when `text` is correct, so review rows before relying on them.
- **Projects:** project experience is retained in `text` and the `projects` section; individual project entries are not parsed.
- **Contact details:** OCR can misread them. An address that no longer looks like an email becomes `null`, but a misread digit or a misread character that still looks valid is kept, so review these on OCR rows.
- **Skills:** the term lists are short, so `soft_skills` is often empty. Case-sensitive terms still match an ordinary word at the start of a sentence, such as "Excel at...".
- **OCR languages:** Tesseract uses its default language, English.
- **Scans:** OCR has only been tested on a text-based CV rendered to an image, not on a real scan.

## Personal data

Rows contain personal data. `email` and `phone` hold contact details, `text` keeps them too, and `source` defaults to the file name, which may include a name. Do not commit rows or sample CVs. `data/*.pdf` and `data/processed/` are already in `.gitignore`, so keep output files there.

## Tests

```sh
uv run pytest tests/module/ocr
```

Tests that need a real CV use the first PDF in `data/` and are skipped if there is none. The OCR comparison test is also skipped if Tesseract is not installed.

## Extending the module

| To change | Edit |
| --- | --- |
| Recognised section headings | `module/terms/headings.yaml` |
| Skill terms | `module/terms/hard_skills.yaml` and `module/terms/soft_skills.yaml`. Add `aliases` for other spellings, and `case_sensitive: true` if the term is also an ordinary word. `tests/module/ocr/test_terms.py` rejects duplicates |
| Degree names | `_DEGREE` in `resume.py` |
| When OCR is used, or its quality | `MIN_TEXT_LAYER_CHARS` and `OCR_DPI` in `extract.py` |
| Table columns | `data/schema.yaml` and the row in `build_record`, in `record.py` |
