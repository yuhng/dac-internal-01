"""The interface a sentence model implements to add semantic matching."""

from collections.abc import Sequence
from typing import Protocol


class Encoder(Protocol):
    version: str

    def encode(self, texts: list[str]) -> Sequence[Sequence[float]]:
        """Returns one L2-normalised vector per text."""
        ...
