"""Classical machine-learning baselines: handcrafted features + Random Forest / SVM.

    python -m research.classical --model rf     # Random Forest on all training photos
    python -m research.classical --model svm    # RBF SVM on up to 400 photos per class

Features (446 per photo, computed on a 128 x 128 copy):
    colour   HSV histograms (32 + 16 + 16 bins), mean/std/skew of R, G, B, H, S, V (82)
    texture  uniform LBP histograms at two radii (28), GLCM contrast, dissimilarity,
             homogeneity, energy, correlation and ASM at two distances (12)
    shape    HOG on a 64 x 64 copy (9 orientations, 16 px cells, 2 x 2 blocks: 324)

Output: research/runs/C1_rf/ or C2_svm/ with model.joblib and config.json, readable
by research/evaluate.py like any CNN run.
"""

from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from research.common import RUNS_DIR, SEED, load_rgb, pv_splits, stratified_subset, write_json

SIZE = 128


def feature_vector(rgb: np.ndarray) -> np.ndarray:
    import cv2
    from scipy.stats import skew
    from skimage.feature import graycomatrix, graycoprops, hog, local_binary_pattern

    img = cv2.resize(rgb, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)  # H in 0..179
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    hist = [np.histogram(hsv[..., 0], 32, (0, 180))[0], np.histogram(hsv[..., 1], 16, (0, 256))[0],
            np.histogram(hsv[..., 2], 16, (0, 256))[0]]
    hist = [h / h.sum() for h in hist]
    moments = []
    for channel in np.concatenate([img, hsv], axis=2).reshape(-1, 6).T.astype(np.float32):
        moments += [channel.mean() / 255, channel.std() / 255, float(np.nan_to_num(skew(channel)))]

    lbp = []
    for p, r in ((8, 1), (16, 2)):
        codes = local_binary_pattern(gray, p, r, method="uniform")
        h = np.histogram(codes, p + 2, (0, p + 2))[0]
        lbp.append(h / h.sum())

    glcm = graycomatrix((gray // 8).astype(np.uint8), distances=[1, 3],
                        angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4], levels=32, symmetric=True, normed=True)
    texture = [graycoprops(glcm, prop).mean(axis=1)
               for prop in ("contrast", "dissimilarity", "homogeneity", "energy", "correlation", "ASM")]

    gray64 = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    shape = hog(gray64, orientations=9, pixels_per_cell=(16, 16), cells_per_block=(2, 2), feature_vector=True)
    return np.concatenate([*hist, moments, *lbp, *texture, shape]).astype(np.float32)


WORKERS = int(os.environ.get("KISAN_WORKERS", os.cpu_count() or 4))


def features(images: np.ndarray) -> np.ndarray:
    """Feature matrix for a batch of uint8 images (used by research/evaluate.py)."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(WORKERS) as pool:
        return np.stack(list(pool.map(feature_vector, images)))


def _features_of_path(path: str) -> np.ndarray:
    return feature_vector(load_rgb(path))


def features_of_paths(paths) -> np.ndarray:
    with ProcessPoolExecutor(WORKERS) as pool:
        return np.stack(list(pool.map(_features_of_path, paths, chunksize=64)))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", choices=["rf", "svm"], default="rf")
    p.add_argument("--svm-per-class", type=int, default=400)
    args = p.parse_args()

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    import joblib

    (train, _val, _test), class_names = pv_splits()
    paths, labels = np.asarray(train[0]), np.asarray(train[1])
    if args.model == "svm":
        keep = stratified_subset(labels, args.svm_per_class)
        paths, labels = paths[keep], labels[keep]
    started = time.time()
    x = features_of_paths(list(paths))
    print(f"{len(x)} training photos, {x.shape[1]} features ({time.time() - started:.0f}s)")

    if args.model == "rf":
        name = "C1_rf"
        clf = RandomForestClassifier(n_estimators=500, class_weight="balanced_subsample",
                                     n_jobs=WORKERS, random_state=SEED)
    else:
        name = "C2_svm"
        clf = SVC(C=10, gamma="scale", probability=True, class_weight="balanced", random_state=SEED)
    pipeline = make_pipeline(StandardScaler(), clf)
    t = time.time()
    pipeline.fit(x, labels)
    run_dir = RUNS_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, run_dir / "model.joblib", compress=3)
    write_json(run_dir / "config.json", {
        "name": name, "backbone": "handcrafted+" + args.model, "features": int(x.shape[1]),
        "train_images": int(len(x)), "training_minutes": round((time.time() - started) / 60, 1),
        "fit_minutes": round((time.time() - t) / 60, 1)})
    print(f"Saved {run_dir / 'model.joblib'}")


if __name__ == "__main__":
    main()
