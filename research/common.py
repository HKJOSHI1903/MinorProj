"""Paths, the fixed train/validation/test split, image loading and the PlantDoc label map.

Every experiment imports its data from here, so all models in the paper are
trained and tested on exactly the same photos.
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PV_DIR = Path(os.environ.get("KISAN_PV_DIR", ROOT / "data" / "plantvillage_full"))
PLANTDOC_DIR = ROOT / "data" / "plantdoc"
RUNS_DIR = ROOT / "research" / "runs"
RESULTS_DIR = ROOT / "research" / "results"
CACHE_DIR = ROOT / "research" / "cache"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
IMAGE_SIZE = 224
SEED = 42


# ---------------------------------------------------------------- PlantVillage

def list_images(data_dir: Path = PV_DIR) -> tuple[list[str], list[int], list[str]]:
    """All image paths with their class index, plus the sorted class names.

    Empty files are skipped (the PlantVillage repository has one 0-byte photo,
    Tomato___healthy/824ae544-...___RS_HL 9900.JPG), so the full set is 54,304 photos.
    """
    class_names = sorted(p.name for p in data_dir.iterdir() if p.is_dir())
    paths: list[str] = []
    labels: list[int] = []
    for index, name in enumerate(class_names):
        for file in sorted((data_dir / name).iterdir()):
            if file.suffix.lower() in IMAGE_SUFFIXES and file.stat().st_size > 0:
                paths.append(str(file))
                labels.append(index)
    return paths, labels, class_names


def split(paths, labels, seed: int = SEED):
    """70% train, 15% validation, 15% test, each with the same class mix (same as kisan.disease.train)."""
    from sklearn.model_selection import train_test_split

    train_p, rest_p, train_y, rest_y = train_test_split(
        paths, labels, test_size=0.30, stratify=labels, random_state=seed)
    val_p, test_p, val_y, test_y = train_test_split(
        rest_p, rest_y, test_size=0.50, stratify=rest_y, random_state=seed)
    return (train_p, train_y), (val_p, val_y), (test_p, test_y)


def pv_splits(data_dir: Path = PV_DIR):
    paths, labels, class_names = list_images(data_dir)
    if not paths:
        raise SystemExit(f"No images in {data_dir}. Run `python scripts/download_data.py --parts 16 "
                         f"--out data/plantvillage_full` first.")
    return split(paths, labels), class_names


def stratified_subset(labels, per_class: int, seed: int = SEED) -> np.ndarray:
    """Indices of at most `per_class` items of every class (all of a class if it has fewer)."""
    labels = np.asarray(labels)
    rng = np.random.default_rng(seed)
    chosen = []
    for c in np.unique(labels):
        idx = np.flatnonzero(labels == c)
        chosen.append(idx if len(idx) <= per_class else rng.choice(idx, per_class, replace=False))
    return np.sort(np.concatenate(chosen))


# ---------------------------------------------------------------- PlantDoc

# PlantDoc folder name -> PlantVillage class. Matched after lower-casing and
# dropping everything but letters, so "Soyabean leaf" and "Soyabean_leaf" both work.
PLANTDOC_TO_PV = {
    "apple scab leaf": "Apple___Apple_scab",
    "apple leaf": "Apple___healthy",
    "apple rust leaf": "Apple___Cedar_apple_rust",
    "bell pepper leaf": "Pepper,_bell___healthy",
    "bell pepper leaf spot": "Pepper,_bell___Bacterial_spot",
    "blueberry leaf": "Blueberry___healthy",
    "cherry leaf": "Cherry_(including_sour)___healthy",
    "corn gray leaf spot": "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "corn leaf blight": "Corn_(maize)___Northern_Leaf_Blight",
    "corn rust leaf": "Corn_(maize)___Common_rust_",
    "peach leaf": "Peach___healthy",
    "potato leaf": "Potato___healthy",
    "potato leaf early blight": "Potato___Early_blight",
    "potato leaf late blight": "Potato___Late_blight",
    "raspberry leaf": "Raspberry___healthy",
    "soyabean leaf": "Soybean___healthy",
    "soybean leaf": "Soybean___healthy",
    "squash powdery mildew leaf": "Squash___Powdery_mildew",
    "strawberry leaf": "Strawberry___healthy",
    "tomato early blight leaf": "Tomato___Early_blight",
    "tomato septoria leaf spot": "Tomato___Septoria_leaf_spot",
    "tomato leaf": "Tomato___healthy",
    "tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "tomato leaf late blight": "Tomato___Late_blight",
    "tomato leaf mosaic virus": "Tomato___Tomato_mosaic_virus",
    "tomato leaf yellow virus": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "tomato mold leaf": "Tomato___Leaf_Mold",
    "tomato two spotted spider mites leaf": "Tomato___Spider_mites Two-spotted_spider_mite",
    "grape leaf": "Grape___healthy",
    "grape leaf black rot": "Grape___Black_rot",
}


def _norm(name: str) -> str:
    return " ".join(re.sub(r"[^a-z]+", " ", name.lower()).split())


def plantdoc_images(part: str, class_names: list[str], dedup_against: str | None = None):
    """(paths, PV label indices, PlantDoc folder names) for PlantDoc `part` ("train" or "test").

    Folders with no PlantVillage counterpart are skipped and reported. With
    `dedup_against="train"`, test photos that are near-duplicates of a train
    photo (see research/dedup.py) are left out.
    """
    folder = PLANTDOC_DIR / part
    if not folder.exists():
        raise SystemExit(f"{folder} is missing. Run `git clone --depth 1 "
                         f"https://github.com/pratikkayal/PlantDoc-Dataset.git data/plantdoc`.")
    index = {name: i for i, name in enumerate(class_names)}
    mapping = {_norm(k): v for k, v in PLANTDOC_TO_PV.items()}
    skip: set[str] = set()
    if dedup_against:
        dup_file = RESULTS_DIR / "dedup" / f"plantdoc_{part}_dups_of_{dedup_against}.json"
        if dup_file.exists():
            skip = set(json.loads(dup_file.read_text(encoding="utf-8"))["duplicates"])
    paths, labels, sources, unmapped = [], [], [], []
    for class_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        target = mapping.get(_norm(class_dir.name))
        if target is None or target not in index:
            unmapped.append(class_dir.name)
            continue
        for file in sorted(class_dir.iterdir()):
            if file.suffix.lower() in IMAGE_SUFFIXES and str(file) not in skip:
                paths.append(str(file))
                labels.append(index[target])
                sources.append(class_dir.name)
    if unmapped:
        print(f"PlantDoc {part}: no PlantVillage class for {unmapped}")
    return paths, labels, sources


# ---------------------------------------------------------------- loading

def load_rgb(path: str, size: int = IMAGE_SIZE) -> np.ndarray | None:
    """Photo -> (size, size, 3) uint8, resized the same way as the app (PIL bilinear, no crop)."""
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            return np.asarray(image.resize((size, size), Image.BILINEAR), dtype=np.uint8)
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def load_many(paths, labels, size: int = IMAGE_SIZE, cache_name: str | None = None):
    """Load images into one uint8 array, skipping unreadable files. Cached as .npz when named."""
    if cache_name:
        cache = CACHE_DIR / f"{cache_name}_{size}.npz"
        if cache.exists():
            data = np.load(cache, allow_pickle=False)
            return data["x"], data["y"], list(data["paths"])
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        images = list(pool.map(lambda p: load_rgb(p, size), paths))
    keep = [i for i, im in enumerate(images) if im is not None]
    if len(keep) < len(paths):
        print(f"Skipped {len(paths) - len(keep)} unreadable images")
    x = np.stack([images[i] for i in keep])
    y = np.asarray([labels[i] for i in keep], dtype=np.int64)
    kept_paths = [paths[i] for i in keep]
    if cache_name:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(cache, x=x, y=y, paths=np.asarray(kept_paths))
    return x, y, kept_paths


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=float), encoding="utf-8")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
