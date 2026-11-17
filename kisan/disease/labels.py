"""Turn PlantVillage folder names into readable names and look up treatment advice."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADVICE_PATH = ROOT / "data" / "treatment_advice.json"


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
    """Ignore case and punctuation, so 'Common_rust_' and 'Common_rust' match."""
    return re.sub(r"[^a-z0-9]", "", class_name.lower())


@lru_cache(maxsize=1)
def _load() -> dict:
    raw = json.loads(ADVICE_PATH.read_text(encoding="utf-8"))
    raw["classes"] = {_key(name): entry for name, entry in raw["classes"].items()}
    return raw


def treatment_advice(class_name: str) -> dict | None:
    """Advice for one class.

    Disease classes return cause, symptoms, organic, chemical and prevention.
    Healthy classes return the general care tips (organic and prevention only).
    Returns None when nothing is stored for the class.
    """
    data = _load()
    if parse_label(class_name).healthy:
        return data["healthy"]
    return data["classes"].get(_key(class_name))


def advice_disclaimer() -> str:
    return _load()["_meta"]["disclaimer"]
