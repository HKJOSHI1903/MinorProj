"""Image degradations used to measure robustness (the evaluation side).

Each function takes a uint8 (H, W, 3) RGB image at the model input size and
returns a degraded uint8 image of the same size. Random ones take a numpy
Generator, so every run degrades every photo identically.

These are written with numpy/OpenCV on purpose: the training augmentation in
research/augment.py is a separate TensorFlow implementation, so a robust model
is never tested on the exact code it was trained with. Motion blur, speckle
and salt-and-pepper noise are not used in training at all; they are the
"unseen corruption" test (as in ImageNet-C, Hendrycks & Dietterich 2019).
"""

from __future__ import annotations

import cv2
import numpy as np


def _clip(x: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(x), 0, 255).astype(np.uint8)


# ------------------------------------------------------------ illumination

def brightness(img, factor: float, rng=None):
    """Exposure change: every pixel times `factor` (0.2 = very dark, 2.0 = over-exposed)."""
    return _clip(img.astype(np.float32) * factor)


def contrast(img, factor: float, rng=None):
    """Blend with the mean grey level (PIL ImageEnhance.Contrast): <1 flattens, >1 stretches."""
    f = img.astype(np.float32)
    mean = (0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]).mean()
    return _clip(mean + factor * (f - mean))


def gamma(img, g: float, rng=None):
    """Non-linear tone change: g > 1 darkens shadows, g < 1 lifts them."""
    return _clip(255.0 * (img.astype(np.float32) / 255.0) ** g)


def color_cast(img, k: float, rng=None):
    """White-balance error: k > 0 warm (more red, less blue), k < 0 cool."""
    f = img.astype(np.float32)
    f[..., 0] *= 1 + k
    f[..., 2] *= 1 - k
    return _clip(f)


# ------------------------------------------------------------ noise

def gaussian_noise(img, sigma: float, rng):
    """Additive sensor noise with standard deviation `sigma` (0..255 scale)."""
    if sigma <= 0:
        return img.copy()
    return _clip(img.astype(np.float32) + rng.normal(0, sigma, img.shape))


def salt_pepper(img, amount: float, rng):
    """Impulse noise: `amount` of the pixels set to pure black or white."""
    out = img.copy()
    if amount <= 0:
        return out
    mask = rng.random(img.shape[:2])
    out[mask < amount / 2] = 0
    out[(mask >= amount / 2) & (mask < amount)] = 255
    return out


def speckle(img, var: float, rng):
    """Multiplicative noise img * (1 + n), n ~ N(0, var)."""
    if var <= 0:
        return img.copy()
    f = img.astype(np.float32)
    return _clip(f + f * rng.normal(0, np.sqrt(var), img.shape))


# ------------------------------------------------------------ blur and compression

def gaussian_blur(img, sigma: float, rng=None):
    """Defocus-like blur."""
    if sigma <= 0:
        return img.copy()
    return cv2.GaussianBlur(img, (0, 0), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_REFLECT)


def motion_blur(img, length: int, rng):
    """Camera-shake blur: a line kernel of `length` pixels at a random angle."""
    length = int(length)
    if length <= 1:
        return img.copy()
    kernel = np.zeros((length, length), np.float32)
    kernel[length // 2, :] = 1.0
    angle = float(rng.uniform(0, 180))
    rot = cv2.getRotationMatrix2D(((length - 1) / 2, (length - 1) / 2), angle, 1.0)
    kernel = cv2.warpAffine(kernel, rot, (length, length))
    kernel /= max(kernel.sum(), 1e-6)
    return cv2.filter2D(img, -1, kernel, borderType=cv2.BORDER_REFLECT)


def jpeg(img, quality: int, rng=None):
    """JPEG re-compression at `quality` (100 = best). WhatsApp-style sharing is around 50-70."""
    if quality >= 100:
        return img.copy()
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR),
                           [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    return cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def resolution(img, side: int, rng=None):
    """Low resolution: shrink to `side` x `side` (area averaging), then back up (bilinear),
    as the app does when a small or distant leaf is resized to the model input."""
    h, w = img.shape[:2]
    if side >= min(h, w):
        return img.copy()
    small = cv2.resize(img, (side, side), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


# ------------------------------------------------------------ the sweep

# family -> (function, levels, clean level, axis label, used in robust training?)
FAMILIES = {
    "brightness": (brightness, [0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0],
                   1.0, "Brightness factor", True),
    "contrast": (contrast, [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0], 1.0, "Contrast factor", True),
    "gamma": (gamma, [0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0], 1.0, "Gamma", True),
    "color_cast": (color_cast, [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5], 0.0,
                   "Colour cast (cool <- 0 -> warm)", True),
    "gaussian_noise": (gaussian_noise, [0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80], 0, "Gaussian noise sigma", True),
    "salt_pepper": (salt_pepper, [0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.15, 0.2], 0, "Salt & pepper amount", False),
    "speckle": (speckle, [0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5], 0, "Speckle variance", False),
    "gaussian_blur": (gaussian_blur, [0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7], 0, "Gaussian blur sigma (px)", True),
    "motion_blur": (motion_blur, [1, 3, 5, 7, 9, 13, 17, 21, 29], 1, "Motion blur length (px)", False),
    "jpeg": (jpeg, [100, 90, 75, 50, 30, 20, 15, 10, 5, 2], 100, "JPEG quality", True),
    "resolution": (resolution, [224, 192, 160, 128, 96, 80, 64, 48, 32, 24, 16], 224, "Effective resolution (px)", True),
}

# Low light is dark AND noisy at the same time: a 2-D grid.
LOW_LIGHT_BRIGHTNESS = [0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0]
LOW_LIGHT_NOISE = [0, 5, 10, 20, 30, 45]


def low_light(img, brightness_factor: float, sigma: float, rng):
    """Darken first, then add sensor noise (noise does not scale down with the light)."""
    return gaussian_noise(brightness(img, brightness_factor), sigma, rng)


def apply(images: np.ndarray, fn, level, seed: int = 0) -> np.ndarray:
    """Degrade a batch. Each image gets its own seeded generator, so results do not depend
    on batch order or on which other images are in the batch."""
    out = np.empty_like(images)
    for i, img in enumerate(images):
        out[i] = fn(img, level, np.random.default_rng((seed, i)))
    return out
