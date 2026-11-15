"""OpenAI token usage and estimated cost for this pipeline's LLM calls, as JSON.

EvidenceAssessor calls record() after every request; this script sums the log:
    .venv/bin/python -m improvement.src.usage
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
LOG_PATH = OUTPUT_DIR / "openai_usage.jsonl"
REPORT_PATH = OUTPUT_DIR / "openai_usage.json"

# shortcut: hand-copied USD per 1M tokens (input, cached input, output); update when OpenAI changes prices
PRICES = {"gpt-4o-mini": (0.15, 0.075, 0.60), "gpt-4o": (2.50, 1.25, 10.00)}
TOKEN_FIELDS = ("requests", "input_tokens", "cached_input_tokens", "output_tokens")


def record(response, path: Optional[Path] = None) -> None:
    """Append one chat completion's token usage to the JSONL log."""
    usage = response.usage
    if usage is None:
        return
    details = usage.prompt_tokens_details
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": response.model,
        "input_tokens": usage.prompt_tokens,
        "cached_input_tokens": (details.cached_tokens or 0) if details else 0,
        "output_tokens": usage.completion_tokens,
    }
    entry["estimated_cost_usd"] = estimate_cost(entry["model"], entry)
    path = path or LOG_PATH
    path.parent.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def estimate_cost(model: str, totals: dict) -> Optional[float]:
    # response.model is a dated snapshot, e.g. gpt-4o-mini-2024-07-18; longest prefix avoids gpt-4o matching first
    base = max((m for m in PRICES if model.startswith(m)), key=len, default=None)
    if base is None:
        return None
    inp, cached, out = PRICES[base]
    uncached = totals["input_tokens"] - totals["cached_input_tokens"]
    return round((uncached * inp + totals["cached_input_tokens"] * cached + totals["output_tokens"] * out) / 1e6, 6)


def summarize(entries: list[dict]) -> dict:
    by_model = defaultdict(lambda: dict.fromkeys(TOKEN_FIELDS, 0))
    by_day = defaultdict(lambda: dict.fromkeys(TOKEN_FIELDS, 0))
    for e in entries:
        for totals in (by_model[e["model"]], by_day[e["timestamp"][:10]]):
            totals["requests"] += 1
            for field in TOKEN_FIELDS[1:]:
                totals[field] += e[field]

    for model, totals in by_model.items():
        totals["estimated_cost_usd"] = estimate_cost(model, totals)

    known = [t["estimated_cost_usd"] for t in by_model.values() if t["estimated_cost_usd"] is not None]
    return {
        "requests": len(entries),
        "first_call": entries[0]["timestamp"] if entries else None,
        "last_call": entries[-1]["timestamp"] if entries else None,
        "estimated_cost_usd": round(sum(known), 6),  # excludes models missing from PRICES
        "by_model": dict(by_model),
        "by_day": dict(sorted(by_day.items())),
    }


def main() -> dict:
    lines = LOG_PATH.read_text(encoding="utf-8").splitlines() if LOG_PATH.exists() else []
    report = summarize([json.loads(line) for line in lines if line.strip()])
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
