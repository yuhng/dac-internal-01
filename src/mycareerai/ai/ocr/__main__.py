"""Usage: uv run python -m mycareerai.ai.ocr resume.pdf --output row.json"""

import argparse
import json
import sys
from pathlib import Path

from .extract import OcrError
from .record import build_record


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn a resume PDF into a row matching data/schema.json.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, help="file to write; prints to stdout if omitted")
    parser.add_argument("--source", help="where the document came from; defaults to the file name")
    parser.add_argument("--license", default="unknown", help="terms the document can be used under")
    parser.add_argument("--force-ocr", action="store_true", help="use OCR even when a text layer exists")
    args = parser.parse_args()

    try:
        record = build_record(args.pdf, source=args.source, license=args.license, force_ocr=args.force_ocr)
    except OcrError as err:
        sys.exit(str(err))

    output = json.dumps(record, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(output + "\n")
    else:
        print(output)


if __name__ == "__main__":
    main()
