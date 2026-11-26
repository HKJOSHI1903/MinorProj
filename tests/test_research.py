"""Tests for the paper's evaluation code: degradations, quality gate, correction, metrics."""

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from kisan.disease import quality
from kisan.disease.enhance import enhance_array

ROOT = Path(__file__).resolve().parents[1]


def leaf(size=224, seed=0) -> np.ndarray:
    """A synthetic textured green 'leaf' on a grey background."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:size, :size]
    img = np.full((size, size, 3), 150, np.float32)
    mask = ((yy - size / 2) / (size * 0.42)) ** 2 + ((xx - size / 2) / (size * 0.3)) ** 2 < 1
    texture = 25 * np.sin(xx / 3.0) * np.cos(yy / 5.0) + rng.normal(0, 3, (size, size))
    img[mask] = np.stack([60 + texture, 140 + texture, 50 + texture / 2], axis=-1)[mask]
    for _ in range(12):  # brown spots
        cy, cx = rng.integers(40, size - 40, 2)
        img[(yy - cy) ** 2 + (xx - cx) ** 2 < 36] = [120, 80, 30]
    return np.clip(img, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ degradations

D = pytest.importorskip("research.degradations", reason="needs opencv")


@pytest.mark.parametrize("family", list(D.FAMILIES))
def test_every_degradation_keeps_shape_and_is_identity_at_the_clean_level(family):
    fn, levels, clean, _axis, _seen = D.FAMILIES[family]
    img = leaf()
    assert clean in levels
    out = fn(img, clean, np.random.default_rng(0))
    assert out.shape == img.shape and out.dtype == np.uint8
    assert np.abs(out.astype(int) - img.astype(int)).max() <= 1
    for level in levels:
        degraded = fn(img, level, np.random.default_rng(0))
        assert degraded.shape == img.shape and degraded.dtype == np.uint8


def test_degradations_are_deterministic_per_seed():
    img = leaf()
    a = D.apply(img[None].repeat(3, 0), D.gaussian_noise, 20, seed=5)
    b = D.apply(img[None].repeat(3, 0), D.gaussian_noise, 20, seed=5)
    assert np.array_equal(a, b)
    assert not np.array_equal(a[0], a[1])  # each image gets its own noise


def test_degradations_move_the_matching_quality_measure():
    img = leaf()
    base = quality.measure_array(img, 224)
    dark = quality.measure_array(D.brightness(img, 0.2), 224)
    noisy = quality.measure_array(D.gaussian_noise(img, 30, np.random.default_rng(0)), 224)
    blurred = quality.measure_array(D.gaussian_blur(img, 3), 224)
    flat = quality.measure_array(D.contrast(img, 0.2), 224)
    assert dark["brightness"] < 0.3 * base["brightness"]
    assert noisy["noise"] > base["noise"] + 15
    assert blurred["sharpness"] < 0.2 * base["sharpness"]
    assert flat["contrast"] < 0.3 * base["contrast"]


# ------------------------------------------------------------------ quality gate

def test_good_photo_has_no_issues():
    report = quality.assess(Image.fromarray(leaf(512)), thresholds=quality.DEFAULT_THRESHOLDS)
    assert report.ok, report.issues


@pytest.mark.parametrize("make, issue", [
    (lambda im: (im * 0.12).astype(np.uint8), "too_dark"),
    (lambda im: np.clip(im.astype(int) + 140, 0, 255).astype(np.uint8), "too_bright"),
    (lambda im: np.asarray(Image.fromarray(im).resize((48, 48))), "low_resolution"),
])
def test_bad_photos_are_flagged(make, issue):
    # Pinned to the built-in defaults: models/quality_thresholds.json holds the deployed
    # model's measured limits, which are far more lenient.
    report = quality.assess(Image.fromarray(make(leaf(512))), thresholds=quality.DEFAULT_THRESHOLDS)
    assert issue in report.issues
    assert report.to_json()["advice"]


def test_noise_is_judged_at_model_resolution():
    t = quality.DEFAULT_THRESHOLDS
    noisy_224 = np.clip(leaf(224) + np.random.default_rng(1).normal(0, 35, (224, 224, 3)), 0, 255).astype(np.uint8)
    assert "noisy" in quality.assess(Image.fromarray(noisy_224), thresholds=t).issues
    # The same grain on a large photo is averaged away when it is shrunk to 224 px.
    noisy_1024 = np.clip(leaf(1024) + np.random.default_rng(1).normal(0, 35, (1024, 1024, 3)), 0, 255).astype(np.uint8)
    assert "noisy" not in quality.assess(Image.fromarray(noisy_1024), thresholds=t).issues


def test_deployed_gate_thresholds_are_sane():
    """models/quality_thresholds.json comes from research/thresholds.py; every value must be usable."""
    t = quality.load_thresholds.__wrapped__()
    assert 0 <= t["min_brightness"] < 60 < 180 < t["max_brightness"] <= 255
    assert 0 < t["min_contrast"] < 30 and 0 < t["max_noise"] < 100 and 0 < t["min_sharpness"] < 500
    assert 16 <= t["min_side"] <= 224 and 0 < t["max_underexposed"] <= 1 and 0 < t["max_overexposed"] <= 1


def test_blurred_photo_is_flagged():
    D_blur = pytest.importorskip("research.degradations").gaussian_blur
    report = quality.assess(Image.fromarray(D_blur(leaf(224), 6)), thresholds=quality.DEFAULT_THRESHOLDS)
    assert "blurry" in report.issues
    assert "blurry" in quality.assess(Image.fromarray(D_blur(leaf(224), 6))).issues   # deployed gate too


def test_noise_estimate_tracks_added_noise():
    flat = np.full((224, 224, 3), 128, np.uint8)
    for sigma in (5, 15, 30):
        noisy = np.clip(flat + np.random.default_rng(0).normal(0, sigma, flat.shape), 0, 255).astype(np.uint8)
        assert quality.measure_array(noisy, 224)["noise"] == pytest.approx(sigma, rel=0.15)


def test_thresholds_file_overrides_defaults(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"thresholds": {"min_brightness": 77.0, "unknown": 1}}))
    t = quality.load_thresholds.__wrapped__(str(path))
    assert t["min_brightness"] == 77.0 and "unknown" not in t
    assert t["max_noise"] == quality.DEFAULT_THRESHOLDS["max_noise"]


# ------------------------------------------------------------------ correction

def test_enhance_leaves_good_photos_untouched():
    img = leaf()
    assert enhance_array(img) is img


def test_enhance_brightens_dark_photos():
    dark = (leaf() * 0.15).astype(np.uint8)
    fixed = enhance_array(dark)
    assert quality.luma(fixed).mean() > 3 * quality.luma(dark).mean()


# ------------------------------------------------------------------ metrics

def test_metrics_perfect_and_random():
    from research import metrics as M

    y = np.repeat(np.arange(5), 20)
    perfect = np.eye(5)[y] * 0.9 + 0.02
    s = M.summarize(y, perfect, ci=True, n_boot=50)
    assert s["accuracy"] == 1 and s["macro_f1"] == 1 and s["mcc"] == pytest.approx(1)
    assert s["macro_roc_auc"] == pytest.approx(1)
    assert s["ci95"]["accuracy"] == [1.0, 1.0]
    uniform = np.full((100, 5), 0.2)
    assert M.summarize(y, uniform, ci=False)["selective"]["curve"][0]["coverage"] == 1.0


def test_mcnemar_detects_a_real_difference_and_ignores_none():
    from research import metrics as M

    y = np.zeros(200, int)
    good = y.copy()
    bad = y.copy()
    bad[:60] = 1
    assert M.mcnemar(y, good, bad)["p_value"] < 1e-6
    assert M.mcnemar(y, good, good)["p_value"] == 1.0


def test_calibration_error_is_zero_when_confidence_matches_accuracy():
    from research import metrics as M

    y = np.array([0] * 8 + [1] * 2)
    probs = np.tile([0.8, 0.2], (10, 1))   # always says class 0 with 80%, right 80% of the time
    assert M.calibration(y, probs)["ece"] == pytest.approx(0, abs=1e-9)


def test_temperature_scaling_sharpens_an_underconfident_model():
    pytest.importorskip("research.degradations", reason="needs opencv")
    from research.evaluate import apply_temperature, fit_temperature

    rng = np.random.default_rng(0)
    y = rng.integers(0, 5, 2000)
    logits = np.eye(5)[y] * 4.0 + rng.normal(0, 1, (2000, 5))

    def softmax(z):
        e = np.exp(z - z.max(axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)

    t_original = fit_temperature(y, softmax(logits))
    soft = softmax(logits / 3.0)                      # the same model made 3x less sure
    t = fit_temperature(y, soft)
    assert t == pytest.approx(t_original / 3.0, rel=0.05)
    assert t < 1
    fixed = apply_temperature(soft, t)
    assert np.array_equal(fixed.argmax(1), soft.argmax(1))   # predictions never change
    assert fixed.max(1).mean() > soft.max(1).mean()


# ------------------------------------------------------------------ PlantDoc map and thresholds

def test_plantdoc_map_points_at_real_plantvillage_classes():
    from research.common import PLANTDOC_TO_PV

    classes = set(json.loads((ROOT / "models" / "class_names.json").read_text())["class_names"])
    assert set(PLANTDOC_TO_PV.values()) <= classes


def test_threshold_limit_interpolates_the_crossing():
    from research.thresholds import limit

    rows = [{"level": lvl, "clean_level": 0.0, "accuracy": acc}
            for lvl, acc in [(0, 0.95), (10, 0.94), (20, 0.90), (30, 0.70)]]
    found = limit(rows, "high", tolerance=0.05)
    assert found["level"] == pytest.approx(20.0)
    found = limit(rows, "high", tolerance=0.15)
    assert 20 < found["level"] < 30 and not found["beyond_range"]
