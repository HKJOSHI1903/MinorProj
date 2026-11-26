"""Evaluate trained models: clean test set, cross-dataset (PlantDoc) and robustness sweeps.

    python -m research.evaluate clean      --runs E1 E2 E3
    python -m research.evaluate plantdoc   --runs E1 E2 E3
    python -m research.evaluate robustness --runs E1 E3 [--enhance E1] [--per-class 100]
    python -m research.evaluate lowlight   --runs E1 E3
    python -m research.evaluate calibrate  --runs E1 E3   # temperature scaling on the validation set

A run is a folder in research/runs/ holding model.keras (a CNN from
research/train.py) or model.joblib (the classical baseline from research/classical.py).
`--enhance E1` also evaluates E1 with the automatic photo correction of
kisan/disease/enhance.py applied first (reported as "E1+enh").

For the sweeps every photo is degraded once and the same degraded photo is given
to every model, so the models are compared on identical inputs.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

if __name__ == "__main__":
    os.environ.setdefault("KERAS_BACKEND", "torch")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np  # noqa: E402

from research import degradations as D  # noqa: E402
from research import metrics as M  # noqa: E402
from research.common import (RESULTS_DIR, RUNS_DIR, load_many, plantdoc_images, pv_splits,  # noqa: E402
                             read_json, stratified_subset, write_json)


# ------------------------------------------------------------------ predictors

class KerasPredictor:
    def __init__(self, name: str):
        import keras

        if keras.backend.backend() == "torch":
            import torch

            if torch.cuda.is_available():   # see research/train.py: stop the cache spilling into system RAM
                torch.cuda.set_per_process_memory_fraction(0.8)
        self.name = name
        self.model = keras.models.load_model(RUNS_DIR / name / "model.keras", compile=False)
        self.batch_size = 64

    def __call__(self, images: np.ndarray) -> np.ndarray:
        out = []
        for i in range(0, len(images), 256):
            batch = images[i:i + 256].astype(np.float32)
            out.append(self._predict(batch))
        return np.concatenate(out)

    def _predict(self, batch: np.ndarray) -> np.ndarray:
        """Predict, halving the batch size when the GPU runs out of memory (large backbones)."""
        import gc

        while True:
            out_of_memory = False
            try:
                return np.asarray(self.model.predict(batch, batch_size=self.batch_size, verbose=0), dtype=np.float32)
            except Exception as error:   # torch.OutOfMemoryError, wrapped by Keras
                if "OutOfMemory" not in type(error).__name__ + repr(error) or self.batch_size <= 4:
                    raise
                out_of_memory = True
            # Outside the except block: the traceback (and the GPU tensors its frames hold) is gone.
            if out_of_memory:
                import torch

                gc.collect()
                torch.cuda.empty_cache()
                self.batch_size //= 2
                print(f"  {self.name}: out of GPU memory, predicting in batches of {self.batch_size}", flush=True)


class ClassicalPredictor:
    def __init__(self, name: str):
        import joblib

        from research.classical import features

        self.name = name
        self.pipeline = joblib.load(RUNS_DIR / name / "model.joblib")
        self.features = features

    def __call__(self, images: np.ndarray) -> np.ndarray:
        probs = self.pipeline.predict_proba(self.features(images))
        full = np.zeros((len(images), 38), np.float32)      # classifier may have been fit on all 38 classes
        full[:, self.pipeline.classes_] = probs
        return full


class EnhancedPredictor:
    """Runs the app's automatic photo correction before the model."""

    def __init__(self, inner):
        from kisan.disease.enhance import enhance_array

        self.inner, self.name, self.enhance = inner, f"{inner.name}+enh", enhance_array

    def __call__(self, images: np.ndarray) -> np.ndarray:
        return self.inner(np.stack([self.enhance(im) for im in images]))


def load_predictor(name: str):
    if (RUNS_DIR / name / "model.keras").exists():
        return KerasPredictor(name)
    if (RUNS_DIR / name / "model.joblib").exists():
        return ClassicalPredictor(name)
    raise SystemExit(f"No model.keras or model.joblib in {RUNS_DIR / name}")


def predictors_for(args):
    loaded = {name: load_predictor(name) for name in args.runs}
    out = list(loaded.values())
    for name in args.enhance or []:
        out.append(EnhancedPredictor(loaded.get(name) or load_predictor(name)))
    return out


# ------------------------------------------------------------------ data

def pv_test():
    (_, _, (test_p, test_y)), class_names = pv_splits()
    x, y, _ = load_many(test_p, test_y, cache_name="pv_test")
    return x, y, class_names


def crop_of(name: str) -> str:
    return name.split("___")[0]


# ------------------------------------------------------------------ clean test set

def cmd_clean(args):
    x, y, class_names = pv_test()
    for model in predictors_for(args):
        t = time.time()
        probs = model(x)
        seconds = time.time() - t
        summary = M.summarize(y, probs, labels=range(len(class_names)))
        summary["images_per_second"] = len(x) / seconds
        out = RUNS_DIR / model.name.split("+")[0] / "eval"
        suffix = "_enh" if "+enh" in model.name else ""
        write_json(out / f"pv_test{suffix}.json",
                   {"summary": summary, "per_class": M.per_class(y, probs, class_names)})
        np.savez_compressed(out / f"pv_test_probs{suffix}.npz", y=y, probs=probs.astype(np.float16))
        print(f"{model.name:28s} acc {M.fmt_ci(summary['accuracy'], summary['ci95']['accuracy'])}  "
              f"macro-F1 {M.fmt_ci(summary['macro_f1'], summary['ci95']['macro_f1'])}  "
              f"MCC {summary['mcc']:.4f}  ECE {summary['calibration']['ece']:.4f}")


# ------------------------------------------------------------------ cross-dataset

def cross_dataset_metrics(y, probs, class_names) -> dict:
    present = sorted(set(y.tolist()))
    open_set = M.summarize(y, probs, labels=present)
    # Restricted: the model may only choose among the classes that occur in PlantDoc.
    masked = np.zeros_like(probs)
    masked[:, present] = probs[:, present]
    masked /= np.clip(masked.sum(axis=1, keepdims=True), 1e-12, None)
    restricted = M.summarize(y, masked, labels=present)
    pred = probs.argmax(axis=1)
    crops = np.array([crop_of(n) for n in class_names])
    healthy = np.array(["healthy" in n.lower() for n in class_names])
    return {
        "classes": [class_names[c] for c in present],
        "open_set": open_set,
        "restricted": restricted,
        "crop_accuracy": float((crops[pred] == crops[y]).mean()),
        "healthy_vs_diseased_accuracy": float((healthy[pred] == healthy[y]).mean()),
        "per_class": M.per_class(y, probs, class_names, labels=present),
    }


def cmd_plantdoc(args):
    _, class_names = pv_splits()
    sets = {}
    for variant, dedup in (("test", None), ("test_dedup", "train")):
        paths, labels, _ = plantdoc_images("test", class_names, dedup_against=dedup)
        x, y, _ = load_many(paths, labels, cache_name=f"plantdoc_{variant}")
        sets[variant] = (x, y)
        print(f"PlantDoc {variant}: {len(y)} photos in {len(set(y.tolist()))} classes")
    for model in predictors_for(args):
        report = {}
        for variant, (x, y) in sets.items():
            probs = model(x)
            report[variant] = cross_dataset_metrics(y, probs, class_names)
            out = RUNS_DIR / model.name.split("+")[0] / "eval"
            suffix = "_enh" if "+enh" in model.name else ""
            np.savez_compressed(out / f"plantdoc_{variant}_probs{suffix}.npz", y=y, probs=probs.astype(np.float16))
        suffix = "_enh" if "+enh" in model.name else ""
        write_json(RUNS_DIR / model.name.split("+")[0] / "eval" / f"plantdoc{suffix}.json", report)
        r = report["test"]
        print(f"{model.name:28s} open acc {r['open_set']['accuracy']:.4f} macro-F1 {r['open_set']['macro_f1']:.4f} | "
              f"restricted acc {r['restricted']['accuracy']:.4f} | crop {r['crop_accuracy']:.4f} | "
              f"healthy/diseased {r['healthy_vs_diseased_accuracy']:.4f}")


# ------------------------------------------------------------------ robustness sweeps

def _quality_stats(images: np.ndarray) -> dict:
    from kisan.disease.quality import measure_array

    rows = [measure_array(im, 224) for im in images]
    return {k: float(np.median([r[k] for r in rows])) for k in rows[0] if k != "min_side"}


def _degrade(x, fn, level, seed):
    from concurrent.futures import ThreadPoolExecutor

    chunks = np.array_split(np.arange(len(x)), os.cpu_count() or 4)

    def work(idx):
        out = np.empty((len(idx),) + x.shape[1:], np.uint8)
        for j, i in enumerate(idx):
            out[j] = fn(x[i], level, np.random.default_rng((seed, int(i))))
        return idx, out

    result = np.empty_like(x)
    with ThreadPoolExecutor(len(chunks)) as pool:
        for idx, out in pool.map(work, chunks):
            result[idx] = out
    return result


def cmd_robustness(args):
    import csv

    x_all, y_all, class_names = pv_test()
    idx = stratified_subset(y_all, args.per_class)
    x, y = x_all[idx], y_all[idx]
    labels = range(len(class_names))
    models = predictors_for(args)
    families = args.families.split(",") if args.families else list(D.FAMILIES)
    out_dir = RESULTS_DIR / "robustness"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Robustness subset: {len(y)} photos ({args.per_class} per class at most), "
          f"{len(models)} models, families {families}")

    for family in families:
        fn, levels, clean, axis, trained = D.FAMILIES[family]
        rows = []
        for level in levels:
            t = time.time()
            xd = _degrade(x, fn, level, seed=hash(family) % 10_000)
            quality = _quality_stats(xd[:: max(1, len(xd) // 600)])
            for model in models:
                m = M.fast(y, model(xd), labels)
                rows.append({"model": model.name, "family": family, "level": level, "clean_level": clean,
                             "seen_in_training": trained, **m, **{f"q_{k}": v for k, v in quality.items()}})
            print(f"{family:15s} {level:>7} " + "  ".join(
                f"{r['model']}={r['accuracy']:.3f}" for r in rows[-len(models):]) + f"  ({time.time() - t:.0f}s)")
        path = out_dir / f"{family}.csv"
        existing = []
        if path.exists():   # keep results of models not re-run now
            with path.open(encoding="utf-8") as f:
                existing = [r for r in csv.DictReader(f) if r["model"] not in {m.name for m in models}]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(existing + rows)


def cmd_lowlight(args):
    import csv

    x_all, y_all, class_names = pv_test()
    idx = stratified_subset(y_all, args.per_class)
    x, y = x_all[idx], y_all[idx]
    models = predictors_for(args)
    rows = []
    for b in D.LOW_LIGHT_BRIGHTNESS:
        for s in D.LOW_LIGHT_NOISE:
            xd = _degrade(x, lambda im, _lvl, rng: D.low_light(im, b, s, rng), None, seed=7)
            for model in models:
                m = M.fast(y, model(xd), range(len(class_names)))
                rows.append({"model": model.name, "brightness": b, "noise_sigma": s, **m})
            print(f"low light b={b:<5} sigma={s:<3} " + "  ".join(
                f"{r['model']}={r['accuracy']:.3f}" for r in rows[-len(models):]))
    path = RESULTS_DIR / "robustness" / "low_light.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            existing = [r for r in csv.DictReader(f) if r["model"] not in {m.name for m in models}]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(existing + rows)


# ------------------------------------------------------------------ calibration

def apply_temperature(probs: np.ndarray, t: float) -> np.ndarray:
    """softmax(z / t) from softmax(z): divide the log-probabilities by t and renormalise."""
    logp = np.log(np.clip(probs.astype(np.float64), 1e-12, 1.0)) / t
    logp -= logp.max(axis=1, keepdims=True)
    p = np.exp(logp)
    return p / p.sum(axis=1, keepdims=True)


def fit_temperature(y: np.ndarray, probs: np.ndarray) -> float:
    """Temperature scaling (Guo et al. 2017): the t minimising the validation log loss.

    t > 1 softens an overconfident model, t < 1 sharpens an underconfident one
    (label smoothing makes models underconfident). Predictions do not change.
    """
    from scipy.optimize import minimize_scalar

    rows = np.arange(len(y))

    def nll(t):
        return -np.mean(np.log(np.clip(apply_temperature(probs, t)[rows, y], 1e-12, 1.0)))

    return float(minimize_scalar(nll, bounds=(0.05, 10.0), method="bounded").x)


def cmd_calibrate(args):
    (_, (val_p, val_y), _), _class_names = pv_splits()
    x, y, _ = load_many(val_p, val_y, cache_name="pv_val")
    for model in predictors_for(args):
        if not isinstance(model, KerasPredictor):
            continue
        probs = model(x)
        t = fit_temperature(y, probs)
        report = {"temperature": t, "fitted_on": "PlantVillage validation set",
                  "validation": {"ece_before": M.calibration(y, probs)["ece"],
                                 "ece_after": M.calibration(y, apply_temperature(probs, t))["ece"]}}
        eval_dir = RUNS_DIR / model.name / "eval"
        for name in ("pv_test", "plantdoc_test", "plantdoc_test_dedup"):
            path = eval_dir / f"{name}_probs.npz"
            if not path.exists():
                continue
            data = np.load(path)
            yy, pp = data["y"], data["probs"].astype(np.float32)
            entry = {}
            for when, p in (("before", pp), ("after", apply_temperature(pp, t))):
                at = next(r for r in M.selective(yy, p)["curve"] if r["threshold"] == 0.7)
                entry[when] = {"ece": M.calibration(yy, p)["ece"], "log_loss": float(-np.mean(np.log(
                    np.clip(p[np.arange(len(yy)), yy], 1e-12, 1)))), "answered_at_0.7": at["coverage"],
                    "accuracy_when_answered": at["accuracy"], "mean_confidence": float(p.max(1).mean())}
            report[name] = entry
        write_json(RUNS_DIR / model.name / "calibration.json", report)
        pv = report.get("pv_test", {})
        print(f"{model.name:28s} T={t:.3f}  PV ECE {pv.get('before', {}).get('ece', float('nan')):.4f} -> "
              f"{pv.get('after', {}).get('ece', float('nan')):.4f}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=["clean", "plantdoc", "robustness", "lowlight", "calibrate"])
    p.add_argument("--runs", nargs="*", default=[], help="runs to evaluate as they are")
    p.add_argument("--enhance", nargs="*", help="runs to also evaluate with automatic photo correction")
    p.add_argument("--per-class", type=int, default=100, help="robustness subset size per class")
    p.add_argument("--families", default="", help="comma-separated subset of degradation families")
    args = p.parse_args(argv)
    {"clean": cmd_clean, "plantdoc": cmd_plantdoc, "robustness": cmd_robustness, "lowlight": cmd_lowlight,
     "calibrate": cmd_calibrate}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
