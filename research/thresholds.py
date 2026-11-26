"""Derive the minimum photo quality each model needs from the robustness sweeps.

    python -m research.thresholds --model E3 --compare E1 [--tolerance 0.05] [--write-app]

For every degradation family, walk outward from the clean level until accuracy
falls more than `tolerance` below clean accuracy, and interpolate the level
where that happens. The same sweep recorded the measured quality of the degraded
photos (median brightness, contrast, sharpness, noise at that level), so each
limit is also expressed in measurable units, which is what the app's quality
gate checks on a farmer's photo.

Output: research/results/quality_requirements.json and .md; with --write-app,
models/quality_thresholds.json (read by kisan/disease/quality.py).
"""

from __future__ import annotations

import argparse
import csv
import math

from research.common import RESULTS_DIR, ROOT, write_json

# family -> list of (side, measure column, threshold key, direction)
# side "low" = degradation grows as the level decreases (darker, lower resolution, ...).
SIDES = {
    "brightness": [("low", "q_brightness", "min_brightness"), ("high", "q_brightness", "max_brightness"),
                   ("low", "q_underexposed", "max_underexposed"), ("high", "q_overexposed", "max_overexposed")],
    "contrast": [("low", "q_contrast", "min_contrast")],
    "gamma": [("high", "q_brightness", None), ("low", "q_brightness", None)],
    "color_cast": [("low", None, None), ("high", None, None)],
    "gaussian_noise": [("high", "q_noise", "max_noise")],
    "salt_pepper": [("high", "q_noise", "max_noise")],
    "speckle": [("high", "q_noise", "max_noise")],
    "gaussian_blur": [("high", "q_sharpness", "min_sharpness")],
    "motion_blur": [("high", "q_sharpness", "min_sharpness")],
    "jpeg": [("low", None, None)],
    "resolution": [("low", None, "min_side")],
}


def load(family: str, model: str) -> list[dict]:
    path = RESULTS_DIR / "robustness" / f"{family}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["model"] == model]
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return sorted(rows, key=lambda r: r["level"])


def limit(rows: list[dict], side: str, tolerance: float, metric: str = "accuracy"):
    """(level, row interpolation weight info) where accuracy first drops below clean - tolerance."""
    clean_level = rows[0]["clean_level"]
    clean = next(r for r in rows if math.isclose(r["level"], clean_level))
    target = clean[metric] - tolerance
    walk = [r for r in rows if (r["level"] <= clean_level if side == "low" else r["level"] >= clean_level)]
    walk = sorted(walk, key=lambda r: -r["level"] if side == "low" else r["level"])
    for prev, cur in zip(walk, walk[1:]):
        if cur[metric] < target <= prev[metric]:
            w = (prev[metric] - target) / max(prev[metric] - cur[metric], 1e-9)
            return {"level": prev["level"] + w * (cur["level"] - prev["level"]), "prev": prev, "cur": cur, "w": w,
                    "clean": clean[metric], "beyond_range": False}
    last = walk[-1]
    return {"level": last["level"], "prev": last, "cur": last, "w": 0.0, "clean": clean[metric],
            "beyond_range": last[metric] >= target}


def requirements(model: str, tolerance: float) -> dict:
    out = {}
    for family, sides in SIDES.items():
        rows = load(family, model)
        if not rows:
            continue
        for side, measure, key in sides:
            found = limit(rows, side, tolerance)
            entry = {"family": family, "side": side, "level": found["level"],
                     "clean_accuracy": found["clean"], "tolerated_whole_range": found["beyond_range"]}
            if measure:
                a, b, w = found["prev"][measure], found["cur"][measure], found["w"]
                entry["measure"] = measure[2:]
                entry["measured_value"] = a + w * (b - a)
            if key:
                entry["threshold_key"] = key
            out[f"{family}_{side}" + (f"_{measure[2:]}" if measure and measure[2:] not in family else "")] = entry
    return out


# Derived only as a side effect of the brightness sweep: when the model tolerated the whole
# tested range, the value at the range edge says nothing about a limit, so the gate keeps its default.
SECONDARY_KEYS = {"max_underexposed", "max_overexposed"}


def app_thresholds(req: dict) -> dict:
    """Gate thresholds. Several degradation types can set the same threshold (Gaussian and motion
    blur both lower sharpness; three noise types raise the noise estimate): the strictest wins."""
    t = {}
    for entry in req.values():
        key = entry.get("threshold_key")
        if not key:
            continue
        if key in SECONDARY_KEYS and entry["tolerated_whole_range"]:
            continue
        value = entry["level"] if key == "min_side" else entry.get("measured_value")
        if value is None:
            continue
        value = float(value)
        if key in t:
            value = max(t[key], value) if key.startswith("min_") else min(t[key], value)
        t[key] = value
    for key, value in t.items():
        t[key] = round(value, 4 if "exposed" in key else 2)
    if "min_side" in t:
        t["min_side"] = int(math.ceil(t["min_side"]))
    return t


def markdown(models: dict[str, dict], tolerance: float) -> str:
    keys = sorted({k for req in models.values() for k in req})
    lines = [f"Limit = where accuracy falls more than {tolerance * 100:.0f} percentage points below clean.",
             "", "| Degradation | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
    for k in keys:
        cells = []
        for req in models.values():
            e = req.get(k)
            if not e:
                cells.append("-")
                continue
            text = f"{e['level']:.3g}" + (" (whole range ok)" if e["tolerated_whole_range"] else "")
            if "measured_value" in e:
                text += f" -> {e['measure']} {e['measured_value']:.3g}"
            cells.append(text)
        lines.append(f"| {k} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", required=True, help="the model the app uses")
    p.add_argument("--compare", nargs="*", default=[])
    p.add_argument("--tolerance", type=float, default=0.05)
    p.add_argument("--write-app", action="store_true")
    args = p.parse_args()

    models = {name: requirements(name, args.tolerance) for name in [args.model, *args.compare]}
    result = {"tolerance": args.tolerance, "models": models,
              "app_thresholds": {name: app_thresholds(req) for name, req in models.items()}}
    write_json(RESULTS_DIR / "quality_requirements.json", result)
    (RESULTS_DIR / "quality_requirements.md").write_text(markdown(models, args.tolerance), encoding="utf-8")
    print(markdown(models, args.tolerance))
    print("Gate thresholds:", result["app_thresholds"][args.model])
    if args.write_app:
        write_json(ROOT / "models" / "quality_thresholds.json",
                   {"model": args.model, "tolerance": args.tolerance,
                    "thresholds": result["app_thresholds"][args.model]})
        print("Wrote models/quality_thresholds.json")


if __name__ == "__main__":
    main()
