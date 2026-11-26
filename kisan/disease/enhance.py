"""Automatic correction of badly exposed, flat or grainy leaf photos before classification.

Only photos the quality gate (kisan/disease/quality.py) flags are changed; a
good photo passes through untouched, so clean accuracy cannot drop. The order
follows a camera pipeline: remove noise first (so the exposure gain does not
amplify it), then fix exposure, then stretch contrast.

Whether this helps is measured in the paper (research/evaluate.py --enhance):
it is used by the app only where the ablation showed a gain.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .quality import issues_for, luma, measure_array

# Median luma of the PlantVillage training photos the models learned from.
TARGET_BRIGHTNESS = 120.0
MAX_GAIN = 8.0
CORRECTABLE = {"too_dark", "too_bright", "low_contrast", "noisy"}


def enhance_array(rgb: np.ndarray, thresholds: dict | None = None, issues: list[str] | None = None) -> np.ndarray:
    """uint8 RGB at model input size -> corrected uint8 RGB (unchanged when nothing is wrong)."""
    if issues is None:
        issues = issues_for(measure_array(rgb, min(rgb.shape[:2])), thresholds)
    todo = CORRECTABLE.intersection(issues)
    if not todo:
        return rgb

    image = rgb
    if "noisy" in todo:
        image = np.asarray(Image.fromarray(image).filter(ImageFilter.MedianFilter(3)))
    out = image.astype(np.float32)

    if todo & {"too_dark", "too_bright"}:
        mean = float(luma(out).mean())
        gain = float(np.clip(TARGET_BRIGHTNESS / max(mean, 1.0), 1 / MAX_GAIN, MAX_GAIN))
        out = out * gain

    if "low_contrast" in todo:
        y = luma(np.clip(out, 0, 255))
        lo, hi = np.percentile(y, [1, 99])
        if hi - lo > 4:
            mid = (hi + lo) / 2
            out = TARGET_BRIGHTNESS + (out - mid) * (200.0 / (hi - lo))

    return np.clip(np.rint(out), 0, 255).astype(np.uint8)
