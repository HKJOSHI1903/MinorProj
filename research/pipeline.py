"""Run every experiment of the paper in order; finished steps are skipped, so it can be resumed.

    python -m research.pipeline                 # train + evaluate all CNNs on the GPU
    python -m research.pipeline --only E1 E3    # a subset

Each experiment: train (research/train.py) -> clean test set -> PlantDoc
cross-dataset test. Robustness sweeps, deployment measurements, thresholds and
figures run afterwards over all models at once (see research/README.md).

E8 adds PlantDoc field photos to training. Its backbone is chosen by a rule
fixed in advance: the mobile backbone (E3-E5; the app runs on phones) with the
highest PlantVillage *validation* accuracy, so no test photo influences the choice.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

from research.common import ROOT, RUNS_DIR

PY = sys.executable
LOGS = ROOT / "research" / "logs"

# name -> train.py arguments. Batch sizes are the largest that fit in 4 GB of VRAM.
EXPERIMENTS = {
    "E1_mnv2_frozen_std": "--backbone mobilenetv2 --aug standard --head-epochs 6 --fine-tune-epochs 0 --batch-size 32",
    "E2_mnv2_ft_std": "--backbone mobilenetv2 --aug standard --batch-size 64 --lr 3e-4",
    "E3_mnv2_ft_qaa": "--backbone mobilenetv2 --aug robust --batch-size 64 --lr 3e-4",
    "E4_effv2b0_ft_qaa": "--backbone efficientnetv2b0 --aug robust --batch-size 48 --lr 3e-4",
    "E5_mnv3l_ft_qaa": "--backbone mobilenetv3large --aug robust --batch-size 32 --lr 2e-4",
    "E8_best_ft_qaa_plantdoc": None,   # filled in from E3-E5 validation accuracy
    # Batch 16 needs ~4.5 GB for these two and spills into shared memory (very slow), so batch 8.
    # E6 was resumed from its finished head step (--init-from) after that spill was found.
    "E6_resnet50v2_ft_qaa": "--backbone resnet50v2 --aug robust --batch-size 8 --lr 7e-5 --fine-tune-epochs 4",
    "E7_densenet121_ft_qaa": "--backbone densenet121 --aug robust --batch-size 8 --lr 7e-5 --fine-tune-epochs 4",
}
MOBILE_CANDIDATES = ["E3_mnv2_ft_qaa", "E4_effv2b0_ft_qaa", "E5_mnv3l_ft_qaa"]


def finished(name: str) -> bool:
    cfg = RUNS_DIR / name / "config.json"
    return cfg.exists() and "finished" in json.loads(cfg.read_text(encoding="utf-8"))


def step(cmd: list[str], log_name: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    print(f"$ {' '.join(cmd)}", flush=True)
    t = time.time()
    with (LOGS / log_name).open("a", encoding="utf-8") as log:
        code = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                              env={**os.environ, "KERAS_BACKEND": "torch", "PYTHONUNBUFFERED": "1"}).returncode
    print(f"  exit {code} after {(time.time() - t) / 60:.1f} min (log: research/logs/{log_name})", flush=True)
    if code:
        raise SystemExit(code)


def e8_arguments() -> str:
    scores = {}
    for name in MOBILE_CANDIDATES:
        if not finished(name):
            raise SystemExit(f"E8 needs {name} trained first")
        scores[name] = json.loads((RUNS_DIR / name / "config.json").read_text(encoding="utf-8"))["best_val_accuracy"]
    best = max(scores, key=scores.get)
    print(f"E8 backbone from validation accuracy {scores}: {best}", flush=True)
    args = EXPERIMENTS[best]
    return args + " --plantdoc-weight 0.15"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--only", nargs="*", help="experiment name prefixes (e.g. E1 E3)")
    args = p.parse_args()

    for name, train_args in EXPERIMENTS.items():
        if args.only and not any(name.startswith(prefix) for prefix in args.only):
            continue
        if not finished(name):
            train_args = train_args or e8_arguments()
            step([PY, "-m", "research.train", "--name", name, *train_args.split()], f"train_{name}.log")
        eval_dir = RUNS_DIR / name / "eval"
        if not (eval_dir / "pv_test.json").exists():
            step([PY, "-m", "research.evaluate", "clean", "--runs", name], f"eval_{name}.log")
        if not (eval_dir / "plantdoc.json").exists():
            step([PY, "-m", "research.evaluate", "plantdoc", "--runs", name], f"eval_{name}.log")
    print("Pipeline done.")


if __name__ == "__main__":
    main()
