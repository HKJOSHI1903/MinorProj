"""Turn PlantVillage folder names into readable crop and disease names."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

INFO_PATH = Path(__file__).with_name("disease_info.json")


@dataclass(frozen=True)
class Label:
    class_name: str  # the dataset folder name, e.g. "Tomato___Late_blight"
    crop: str        # "Tomato"
    condition: str   # "Late blight" or "Healthy"
    healthy: bool

    @property
    def title(self) -> str:
        return f"{self.crop} - {self.condition}"


def _clean(text: str) -> str:
    text = text.replace("_", " ").replace(" ,", ",")
    return re.sub(r"\s+", " ", text).strip()


def parse_label(class_name: str) -> Label:
    """'Corn_(maize)___Common_rust_' -> crop 'Corn (maize)', condition 'Common rust'."""
    crop, _, condition = class_name.partition("___")
    crop = _clean(crop)
    condition = _clean(condition)
    healthy = condition.lower() == "healthy"
    if healthy:
        condition = "Healthy"
    elif condition:
        condition = condition[0].upper() + condition[1:]
    return Label(class_name=class_name, crop=crop, condition=condition, healthy=healthy)


def _key(class_name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", class_name.lower())


@lru_cache(maxsize=1)
def _load_info() -> dict[str, dict]:
    raw = json.loads(INFO_PATH.read_text(encoding="utf-8"))
    return {_key(name): entry for name, entry in raw.items()}


def disease_info(class_name: str) -> dict | None:
    """Cause, symptoms, treatment and prevention for a disease class, if we have them."""
    return _load_info().get(_key(class_name))
