"""Recommend a crop for a set of soil and weather values, and explain why."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "crop_model.joblib"
PROFILES_PATH = ROOT / "models" / "crop_profiles.json"

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

# What a person could plausibly type. Anything outside is rejected as a mistake.
LIMITS = {
    "N": (0, 300),
    "P": (0, 300),
    "K": (0, 400),
    "temperature": (-10, 60),
    "humidity": (0, 100),
    "ph": (0, 14),
    "rainfall": (0, 1000),
}

# Below this the app says the recommendation is uncertain and points to the KVK.
LOW_CONFIDENCE = 0.70


class CropModelNotTrained(FileNotFoundError):
    pass


class InvalidInput(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


@lru_cache(maxsize=1)
def load():
    """Return (model bundle, profiles). Cached after the first call."""
    if not MODEL_PATH.exists() or not PROFILES_PATH.exists():
        raise CropModelNotTrained("No crop model found. Run `python -m kisan.crop.train` first.")
    import joblib

    return joblib.load(MODEL_PATH), json.loads(PROFILES_PATH.read_text(encoding="utf-8"))


def clean_inputs(values: dict) -> dict[str, float]:
    """Check that all seven values are present, numeric and plausible."""
    cleaned = {}
    for feature in FEATURES:
        raw = values.get(feature)
        if raw is None or raw == "":
            raise InvalidInput(feature, f"{feature} is missing.")
        try:
            number = float(raw)
        except (TypeError, ValueError):
            raise InvalidInput(feature, f"{feature} must be a number.")
        if number != number or number in (float("inf"), float("-inf")):  # NaN or infinity
            raise InvalidInput(feature, f"{feature} must be a number.")
        low, high = LIMITS[feature]
        if not low <= number <= high:
            raise InvalidInput(feature, f"{feature} must be between {low} and {high}.")
        cleaned[feature] = number
    return cleaned


def recommend(values: dict, top_k: int = 3) -> dict:
    """The top_k crops for these values, with the reasons for the first one."""
    inputs = clean_inputs(values)
    bundle, profiles = load()
    model, classes = bundle["model"], bundle["classes"]

    probabilities = model.predict_proba(pd.DataFrame([inputs], columns=FEATURES))[0]
    ranked = sorted(zip(classes, probabilities), key=lambda pair: pair[1], reverse=True)[:top_k]
    best_crop, best_probability = ranked[0]

    # Values the model never saw in training make its answer less trustworthy.
    outside = [feature for feature in FEATURES
               if not profiles["features"][feature]["min"] <= inputs[feature] <= profiles["features"][feature]["max"]]

    # The explanation: is each value inside the range this crop grows in (in the data)?
    profile = profiles["crops"][best_crop]
    reasons = [{
        "feature": feature,
        "value": inputs[feature],
        "low": profile[feature]["low"],
        "high": profile[feature]["high"],
        "fits": profile[feature]["low"] <= inputs[feature] <= profile[feature]["high"],
    } for feature in FEATURES]

    return {
        "recommendation": {"crop": best_crop, "confidence": round(float(best_probability), 4)},
        "alternatives": [{"crop": crop, "confidence": round(float(p), 4)} for crop, p in ranked],
        "low_confidence": bool(best_probability < LOW_CONFIDENCE or outside),
        "threshold": LOW_CONFIDENCE,
        "outside_training_range": outside,
        "reasons": reasons,
        "inputs": inputs,
        "model": bundle["name"],
    }
