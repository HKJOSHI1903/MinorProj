"""Find near-duplicate photos across splits (train/test leakage check).

    python -m research.dedup

A 64-bit difference hash (dHash) is computed for every photo; two photos whose
hashes differ in at most --max-distance bits are treated as the same photo
(re-saved, resized or lightly edited copies). Reports:

    PlantVillage test photos with a near-duplicate in PlantVillage train
    PlantDoc test photos with a near-duplicate in PlantDoc train (these are
        dropped from the "test_dedup" evaluation in research/evaluate.py)

Output: research/results/dedup/*.json
"""

from __future__ import annotations

import argparse
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageOps

from research.common import RESULTS_DIR, plantdoc_images, pv_splits, write_json


def dhash(path: str) -> int | None:
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert("L").resize((9, 8), Image.LANCZOS)
    except (OSError, ValueError):
        return None
    pixels = np.asarray(image, dtype=np.int16)
    bits = (pixels[:, 1:] > pixels[:, :-1]).ravel()
    return int(np.packbits(bits).view(">u8")[0])


def hashes(paths) -> np.ndarray:
    with ThreadPoolExecutor(os.cpu_count()) as pool:
        values = list(pool.map(dhash, paths))
    return np.array([v if v is not None else 0 for v in values], dtype=np.uint64)


_BITS = np.array([bin(i).count("1") for i in range(256)], np.uint8)


def popcount(x: np.ndarray) -> np.ndarray:
    """Number of set bits of every uint64."""
    return _BITS[np.ascontiguousarray(x, dtype=np.uint64).view(np.uint8).reshape(-1, 8)].sum(axis=1)


def near_duplicates(query: np.ndarray, reference: np.ndarray, max_distance: int) -> list[tuple[int, int, int]]:
    """(query index, reference index, Hamming distance) for every query with a close reference."""
    found = []
    for i, h in enumerate(query):
        dist = popcount(np.bitwise_xor(reference, h))
        j = int(dist.argmin())
        if dist[j] <= max_distance:
            found.append((i, j, int(dist[j])))
    return found


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--max-distance", type=int, default=4)
    args = p.parse_args()
    out = RESULTS_DIR / "dedup"

    (train, _val, test), class_names = pv_splits()
    pv_train_h, pv_test_h = hashes(train[0]), hashes(test[0])
    dups = near_duplicates(pv_test_h, pv_train_h, args.max_distance)
    same_class = sum(train[1][j] == test[1][i] for i, j, _ in dups)
    write_json(out / "plantvillage_test_dups_of_train.json", {
        "max_distance": args.max_distance, "test_images": len(test[0]), "near_duplicates": len(dups),
        "same_class": int(same_class),
        "examples": [{"test": test[0][i], "train": train[0][j], "distance": d} for i, j, d in dups[:50]]})
    print(f"PlantVillage: {len(dups)} of {len(test[0])} test photos have a near-duplicate in train "
          f"({same_class} with the same label)")

    pd_train, _, _ = plantdoc_images("train", class_names)
    pd_test, _, _ = plantdoc_images("test", class_names)
    pd_dups = near_duplicates(hashes(pd_test), hashes(pd_train), args.max_distance)
    write_json(out / "plantdoc_test_dups_of_train.json", {
        "max_distance": args.max_distance, "test_images": len(pd_test), "near_duplicates": len(pd_dups),
        "duplicates": sorted({pd_test[i] for i, _, _ in pd_dups}),
        "examples": [{"test": pd_test[i], "train": pd_train[j], "distance": d} for i, j, d in pd_dups[:50]]})
    print(f"PlantDoc: {len(pd_dups)} of {len(pd_test)} test photos have a near-duplicate in train")


if __name__ == "__main__":
    main()
