"""Load the trained model and classify a leaf photo."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .labels import Label, parse_label

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models"
MODEL_FILE = "plant_disease.keras"
CLASSES_FILE = "class_names.json"

# Below 70% the app says the result is uncertain and advises the farmer to
# consult the local Krishi Vigyan Kendra (KVK) or agriculture officer.
LOW_CONFIDENCE = 0.70


@dataclass(frozen=True)
class Prediction:
    label: Label
    confidence: float  # 0..1


class ModelNotTrained(FileNotFoundError):
    pass


@lru_cache(maxsize=1)
def load_model(model_dir: str = str(MODEL_DIR)):
    """Return (model, class_names, image_size, temperature). Cached after the first call."""
    folder = Path(model_dir)
    model_path = folder / MODEL_FILE
    classes_path = folder / CLASSES_FILE
    if not model_path.exists() or not classes_path.exists():
        raise ModelNotTrained(
            f"No trained model in {folder}. Run `python -m kisan.disease.train` first."
        )
    import keras  # imported here so the rest of the package loads without TensorFlow

    meta = json.loads(classes_path.read_text(encoding="utf-8"))
    model = keras.models.load_model(model_path)
    return model, meta["class_names"], int(meta["image_size"]), float(meta.get("temperature", 1.0))


def calibrate(probabilities: np.ndarray, temperature: float) -> np.ndarray:
    """Temperature scaling fitted on the validation set (research/evaluate.py calibrate),
    so that "70% confident" means right about 70% of the time. The ranking never changes."""
    if temperature == 1.0:
        return probabilities
    logp = np.log(np.clip(probabilities.astype("float64"), 1e-12, 1.0)) / temperature
    p = np.exp(logp - logp.max())
    return (p / p.sum()).astype("float32")


def prepare_image(image: Image.Image, image_size: int) -> np.ndarray:
    """Phone photo -> a (1, size, size, 3) float array of 0-255 pixel values.

    The model rescales pixels itself, so this must not normalise them.
    """
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = image.resize((image_size, image_size), Image.BILINEAR)
    return np.asarray(image, dtype="float32")[None, ...]


def predict(image: Image.Image, top_k: int = 3, model_dir: str = str(MODEL_DIR),
            correct: bool | None = None, issues: list[str] | None = None) -> list[Prediction]:
    """The top_k most likely classes for a leaf photo, most likely first.

    With `correct` (default: the KISAN_AUTO_CORRECT environment variable), a photo the
    quality gate flags as too dark, too bright, flat or grainy is corrected first
    (kisan/disease/enhance.py). `issues` are the gate's findings, if already known.
    """
    model, class_names, image_size, temperature = load_model(model_dir)
    batch = prepare_image(image, image_size)
    if correct is None:
        correct = os.environ.get("KISAN_AUTO_CORRECT", "0").lower() in ("1", "true", "yes")
    if correct:
        from .enhance import enhance_array

        batch = enhance_array(batch[0].astype(np.uint8), issues=issues)[None].astype("float32")
    probabilities = calibrate(model.predict(batch, verbose=0)[0], temperature)
    best = np.argsort(probabilities)[::-1][:top_k]
    return [Prediction(parse_label(class_names[i]), float(probabilities[i])) for i in best]
