"""Look up each module's model from models.yaml."""
from functools import cache
from pathlib import Path

import yaml

MODELS_PATH = Path(__file__).with_name("models.yaml")
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
EFFORT_PROVIDERS = {"anthropic"}  # providers whose module code passes effort to the API


@cache
def _load():
    return yaml.safe_load(MODELS_PATH.read_text(encoding="utf-8"))


def _entry(module: str) -> dict:
    entry = _load().get(module)
    if not entry or not str(entry.get("model", "")).strip():
        raise KeyError(f"No model configured for {module!r} in {MODELS_PATH.name}")
    return entry


def model_for(module: str) -> str:
    return _entry(module)["model"]


def effort_for(module: str) -> str | None:
    """Reasoning effort for the module, or None to use the model's default."""
    entry = _entry(module)
    effort = entry.get("effort")
    if effort is None:
        return None
    if effort not in EFFORTS:
        raise ValueError(f"{module}: effort must be one of {sorted(EFFORTS)}, got {effort!r}")
    if entry.get("provider") not in EFFORT_PROVIDERS:
        raise ValueError(f"{module}: effort is not applied for provider {entry.get('provider')!r}; remove it")
    return effort
