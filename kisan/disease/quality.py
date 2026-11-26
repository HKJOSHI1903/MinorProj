"""Measure the quality of a leaf photo and say what is wrong with it.

Every measure except resolution is taken on the 224 x 224 image the model
actually sees, so the thresholds line up with how accuracy changes (the
thresholds come from research/thresholds.py, which measures accuracy on
deliberately degraded test photos).

    brightness   mean luma (Rec. 601), 0..255          too dark / too bright
    contrast     standard deviation of luma, 0..255    flat, washed-out photo
    sharpness    variance of the Laplacian of luma     blurred or out of focus
    noise        Immerkaer (1996) noise sigma per      grainy low-light photo
                 colour channel, averaged, 0..255
                 (noise in a large photo is mostly averaged away by the resize
                 to 224 px, so only noise the model would actually see counts)
    min_side     shorter side of the original, pixels  too small / too far away
    overexposed  share of pixels with luma >= 250      glare, direct sunlight
    underexposed share of pixels with luma <= 5        crushed shadows

Only numpy and Pillow are needed, so the web server can run it on every photo.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_PATH = ROOT / "models" / "quality_thresholds.json"
ANALYSIS_SIZE = 224

# Used until research/thresholds.py has written models/quality_thresholds.json.
DEFAULT_THRESHOLDS = {
    "min_brightness": 40.0,
    "max_brightness": 215.0,
    "min_contrast": 12.0,
    "min_sharpness": 25.0,
    "max_noise": 18.0,
    "min_side": 96,
    "max_overexposed": 0.25,
    "max_underexposed": 0.40,
}

# Issue code -> advice for the farmer (the web app translates by code).
ISSUE_ADVICE = {
    "too_dark": "The photo is too dark. Take it in daylight or move out of the shade.",
    "too_bright": "The photo is too bright. Avoid direct sunlight on the leaf; shade it with your body.",
    "low_contrast": "The photo looks flat or hazy. Clean the camera lens and fill the frame with the leaf.",
    "blurry": "The photo is blurred. Hold the phone steady and tap the leaf on screen to focus.",
    "noisy": "The photo is grainy. Take it in better light.",
    "low_resolution": "The leaf is too small in the photo. Move closer so the leaf fills the frame.",
    "glare": "Part of the leaf is washed out by glare. Change the angle or shade the leaf.",
}


@dataclass(frozen=True)
class QualityReport:
    measures: dict[str, float]
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_json(self) -> dict:
        data = asdict(self)
        data["ok"] = self.ok
        data["advice"] = [ISSUE_ADVICE[code] for code in self.issues]
        data["measures"] = {k: round(float(v), 4) for k, v in self.measures.items()}
        return data


@lru_cache(maxsize=1)
def load_thresholds(path: str = str(THRESHOLDS_PATH)) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    file = Path(path)
    if file.exists():
        stored = json.loads(file.read_text(encoding="utf-8"))
        thresholds.update({k: v for k, v in stored.get("thresholds", stored).items() if k in thresholds})
    return thresholds


def luma(rgb: np.ndarray) -> np.ndarray:
    """uint8 or float RGB (H, W, 3) -> float32 luma (H, W), 0..255."""
    rgb = rgb.astype("float32")
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def laplacian_variance(gray: np.ndarray) -> float:
    """Variance of the 4-neighbour Laplacian: low for blurred images."""
    lap = (gray[1:-1, :-2] + gray[1:-1, 2:] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           - 4.0 * gray[1:-1, 1:-1])
    return float(lap.var())


def noise_sigma(gray: np.ndarray) -> float:
    """Immerkaer's fast noise estimate (CVIU 1996): sigma of additive noise, 0..255.

    The mask [[1,-2,1],[-2,4,-2],[1,-2,1]] cancels smooth image structure, so
    what is left is mostly noise. Leaf texture adds a little on clean photos.
    """
    g = gray.astype("float64")
    conv = (g[:-2, :-2] - 2 * g[:-2, 1:-1] + g[:-2, 2:]
            - 2 * g[1:-1, :-2] + 4 * g[1:-1, 1:-1] - 2 * g[1:-1, 2:]
            + g[2:, :-2] - 2 * g[2:, 1:-1] + g[2:, 2:])
    h, w = g.shape
    return float(np.abs(conv).sum() * math.sqrt(math.pi / 2) / (6.0 * (w - 2) * (h - 2)))


def measure_array(rgb_224: np.ndarray, min_side: int) -> dict[str, float]:
    """All measures for an image already resized to the model input size."""
    gray = luma(rgb_224)
    return {
        "brightness": float(gray.mean()),
        "contrast": float(gray.std()),
        "sharpness": laplacian_variance(gray),
        # Per colour channel, then averaged: same units as the sigma of added RGB noise.
        "noise": float(np.mean([noise_sigma(rgb_224[..., c]) for c in range(3)])),
        "min_side": float(min_side),
        "overexposed": float((gray >= 250).mean()),
        "underexposed": float((gray <= 5).mean()),
    }


def measure(image: Image.Image) -> dict[str, float]:
    image = ImageOps.exif_transpose(image).convert("RGB")
    small = image.resize((ANALYSIS_SIZE, ANALYSIS_SIZE), Image.BILINEAR)
    return measure_array(np.asarray(small), min(image.size))


def issues_for(measures: dict[str, float], thresholds: dict | None = None) -> list[str]:
    t = thresholds or load_thresholds()
    issues = []
    if measures["brightness"] < t["min_brightness"] or measures["underexposed"] > t["max_underexposed"]:
        issues.append("too_dark")
    elif measures["brightness"] > t["max_brightness"]:
        issues.append("too_bright")
    if measures["overexposed"] > t["max_overexposed"] and "too_bright" not in issues:
        issues.append("glare")
    if measures["contrast"] < t["min_contrast"]:
        issues.append("low_contrast")
    if measures["noise"] > t["max_noise"]:
        issues.append("noisy")
    # Noise raises the Laplacian variance, so a noisy photo is not also called sharp-enough-or-blurry.
    elif measures["sharpness"] < t["min_sharpness"]:
        issues.append("blurry")
    if measures["min_side"] < t["min_side"]:
        issues.append("low_resolution")
    return issues


def assess(image: Image.Image, thresholds: dict | None = None) -> QualityReport:
    measures = measure(image)
    return QualityReport(measures=measures, issues=issues_for(measures, thresholds))
