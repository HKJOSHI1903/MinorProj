"""Download PlantDoc (Singh et al., CODS-COMAD 2020), the field-photo test set for the paper.

PlantDoc has 2,598 photos of leaves in real fields and gardens (27 classes,
13 crops) with an official train/test split. Its classes overlap 27 of the 38
PlantVillage classes (see PLANTDOC_TO_PV in research/common.py), so a model
trained on lab photos can be tested on field photos (cross-dataset evaluation).

    python scripts/download_plantdoc.py        # -> data/plantdoc/{train,test}/<class>/

Licence: CC BY 4.0, https://github.com/pratikkayal/PlantDoc-Dataset.

Some PlantDoc file names are web URLs containing "?" and "&", which Windows
cannot store, so `git checkout` fails. Instead the photos of each class folder
are fetched into the git object store (with retries, for unreliable
connections) and written out under cleaned-up names.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_data import remove_tree, run  # noqa: E402

REPO_URL = "https://github.com/pratikkayal/PlantDoc-Dataset.git"
ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ""}
NO_LAZY_FETCH = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
NUL, TAB, NEWLINE = chr(0), chr(9), chr(10)


def stdin_lines(items: list[str]) -> bytes:
    """Bytes for git's stdin. Text mode would turn LF into CRLF on Windows, which git rejects."""
    return (NEWLINE.join(items) + NEWLINE).encode("ascii")


def tree(clone: Path, path: str) -> list[tuple[str, str, str]]:
    """(type, sha, name) of the entries of a folder at HEAD (-z: names are not quoted)."""
    out = subprocess.run(["git", "ls-tree", "-z", f"HEAD:{path}"], cwd=clone, capture_output=True,
                         check=True).stdout.decode("utf-8")
    rows = []
    for entry in filter(None, out.split(NUL)):
        meta, name = entry.split(TAB, 1)
        _mode, kind, sha = meta.split()
        rows.append((kind, sha, name))
    return rows


def missing(clone: Path, shas: list[str]) -> list[str]:
    out = subprocess.run(["git", "cat-file", "--batch-check"], cwd=clone, input=stdin_lines(shas),
                         capture_output=True, env=NO_LAZY_FETCH).stdout.decode("ascii")
    return [line.split()[0] for line in out.splitlines() if line.strip().endswith("missing")]


def fetch_blobs(clone: Path, shas: list[str], attempts: int = 8) -> None:
    for attempt in range(1, attempts + 1):
        todo = missing(clone, shas)
        if not todo:
            return
        subprocess.run(["git", "-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags",
                        "--no-write-fetch-head", "--recurse-submodules=no", "--filter=blob:none", "--stdin"],
                       cwd=clone, input=stdin_lines(todo))
        still = missing(clone, shas)
        if still and attempt < attempts:
            wait = min(60, 5 * attempt)
            print(f"  {len(still)} photos still missing, retrying in {wait}s", flush=True)
            time.sleep(wait)
    if missing(clone, shas):
        raise SystemExit(f"Giving up: {len(missing(clone, shas))} photos could not be fetched")


def safe_name(name: str, used: set[str]) -> str:
    base = name.partition("?")[0]
    stem, dot, suffix = base.rpartition(".")
    if not dot:
        stem, suffix = base, "jpg"
    stem = re.sub(r'[<>:"/\\|?*&=\s]+', "_", stem).strip("._")[:80] or "photo"
    candidate, n = f"{stem}.{suffix.lower()}", 1
    while candidate.lower() in used:
        n += 1
        candidate = f"{stem}_{n}.{suffix.lower()}"
    used.add(candidate.lower())
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "plantdoc")
    args = parser.parse_args()
    out: Path = args.out
    clone = out.parent / "_plantdoc_clone"
    # Files but no clone = a finished download. Files and a clone = an interrupted one: continue it.
    if out.exists() and any(out.iterdir()) and not (clone / ".git").exists():
        print(f"{out} already has files. Delete it first to download again.")
        return 1

    if not (clone / ".git").exists():       # an earlier interrupted run's clone is reused
        if clone.exists():
            remove_tree(clone)
        run("git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1", REPO_URL, str(clone))

    total = 0
    for part in ("train", "test"):
        folders = [name for kind, _sha, name in tree(clone, part) if kind == "tree"]
        for number, folder in enumerate(folders, 1):
            entries = [(sha, name) for kind, sha, name in tree(clone, f"{part}/{folder}")
                       if kind == "blob" and Path(name.partition("?")[0]).suffix.lower() in IMAGE_SUFFIXES]
            print(f"[{part} {number}/{len(folders)}] {folder}: {len(entries)} photos", flush=True)
            fetch_blobs(clone, [sha for sha, _ in entries])
            target = out / part / folder
            target.mkdir(parents=True, exist_ok=True)
            used: set[str] = set()
            for sha, name in entries:
                data = subprocess.run(["git", "cat-file", "blob", sha], cwd=clone, capture_output=True,
                                      check=True).stdout
                (target / safe_name(name, used)).write_bytes(data)
            total += len(entries)

    remove_tree(clone)
    print(f"Saved {total} photos to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
