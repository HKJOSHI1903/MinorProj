"""Download the PlantVillage leaf images (colour version) from GitHub.

The full dataset has about 54,000 images in 38 classes. Image file names start
with a random hex character, so asking for N of the 16 possible characters
gives an even N/16 sample of every class without downloading the rest.

    python scripts/download_data.py            # 4/16 of the images (~13,500)
    python scripts/download_data.py --parts 16 # the full dataset

Needs git on the PATH.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

REPO_URL = "https://github.com/spMohanty/PlantVillage-Dataset.git"
HEX = "0123456789abcdef"
ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def run(*args: str, cwd: Path | None = None, attempts: int = 8) -> None:
    """Run a git command, retrying when the connection drops (blobs already fetched are kept)."""
    print("$", " ".join(args), flush=True)
    for attempt in range(1, attempts + 1):
        if subprocess.run(args, cwd=cwd).returncode == 0:
            return
        if attempt < attempts:
            wait = min(60, 5 * attempt)
            print(f"  failed (attempt {attempt}/{attempts}), retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise SystemExit(f"Giving up after {attempts} attempts: {' '.join(args)}")


def remove_tree(path: Path) -> None:
    """Delete a folder, including the read-only files git leaves on Windows."""

    def on_error(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=on_error)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--parts", type=int, default=4, choices=range(1, 17), metavar="1-16",
                        help="how many sixteenths of the dataset to download (default 4)")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "plantvillage",
                        help="folder that will hold one sub-folder per class")
    args = parser.parse_args()

    out: Path = args.out
    if out.exists() and any(out.iterdir()):
        print(f"{out} already has files. Delete it first to download again.")
        return 1

    clone = out.parent / "_plantvillage_clone"
    clone.parent.mkdir(parents=True, exist_ok=True)

    # One chunk per leading hex character (about 1/16 of the images each), fetched one
    # after the other, so a dropped connection only costs the chunk in progress.
    chunks = []
    for char in HEX[: args.parts]:
        chunk = [f"/raw/color/*/{char}*"]
        if char.isalpha():
            chunk.append(f"/raw/color/*/{char.upper()}*")
        chunks.append(chunk)
    # A few classes (e.g. maize common rust) use names like "RS_Rust 1563.JPG".
    # Fetch all of those and thin them out below.
    chunks.append(["/raw/color/*/[!0-9a-fA-F]*"])

    if (clone / ".git").exists():       # an interrupted run's clone keeps the photos already fetched
        for lock in (clone / ".git").rglob("*.lock"):   # left behind when that run was killed
            lock.unlink()
    else:
        if clone.exists():
            remove_tree(clone)
        run("git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1", REPO_URL, str(clone))
    active: list[str] = []
    for number, chunk in enumerate(chunks, 1):
        active += chunk
        print(f"Chunk {number}/{len(chunks)}", flush=True)
        run("git", "sparse-checkout", "set", "--no-cone", *active, cwd=clone)
        run("git", "checkout", cwd=clone)

    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for class_dir in sorted((clone / "raw" / "color").iterdir()):
        if not class_dir.is_dir():
            continue
        images = sorted(p for p in class_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
        hex_named = [p for p in images if p.name[0].lower() in HEX]
        other = [p for p in images if p.name[0].lower() not in HEX]
        images = hex_named + [p for i, p in enumerate(other) if i % 16 < args.parts]
        if not images:
            continue
        target = out / class_dir.name
        target.mkdir(exist_ok=True)
        for image in images:
            shutil.move(str(image), target / image.name)
        total += len(images)
        print(f"{class_dir.name:55s} {len(images):5d}")

    remove_tree(clone)
    print(f"\nSaved {total} images in {len(list(out.iterdir()))} classes to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
