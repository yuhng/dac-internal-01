"""Usage: uv run python -m mycareerai.module.scoring cv.pdf jd.txt --title "Data Analyst" --company Acme"""

import argparse
import json
import sys
from pathlib import Path

from ..ocr import OcrError, extract_text
from .engine import ScoringError, analyze


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a CV against a job description.")
    parser.add_argument("cv", type=Path, help="CV as a .pdf or plain-text file")
    parser.add_argument("jd", type=Path, help="job description as a plain-text file")
    parser.add_argument("--title", default="")
    parser.add_argument("--company", default="")
    args = parser.parse_args()

    try:
        cv = extract_text(args.cv).text if args.cv.suffix.lower() == ".pdf" else args.cv.read_text()
        result = analyze(args.title, args.company, args.jd.read_text(), cv)
    except (OcrError, ScoringError) as err:
        sys.exit(str(err))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
