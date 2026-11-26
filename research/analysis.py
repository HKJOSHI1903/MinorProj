"""Second phase of the study, after research.pipeline: calibration, robustness sweeps,
deployment measurements, quality thresholds, figures. Finished steps are skipped.

    python -m research.analysis

GPU steps run one after another (two processes on a 4 GB card crash or spill into
system RAM). The deployment step measures CPU latency, so it runs last, alone.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from research.common import RESULTS_DIR, ROOT, RUNS_DIR

PY = sys.executable
LOGS = ROOT / "research" / "logs"

MAIN = ["E1_mnv2_frozen_std", "E2_mnv2_ft_std", "E3_mnv2_ft_qaa", "E4_effv2b0_ft_qaa", "E5_mnv3l_ft_qaa",
        "E8_best_ft_qaa_plantdoc"]
HEAVY = ["E6_resnet50v2_ft_qaa", "E7_densenet121_ft_qaa"]
CNNS = MAIN[:5] + HEAVY + MAIN[5:]                 # figure order: E1..E7, then E8
CLASSICAL = ["C1_rf", "C2_svm"]
ENHANCE = ["E1_mnv2_frozen_std", "E3_mnv2_ft_qaa"]
HEAVY_FAMILIES = "brightness,contrast,gaussian_noise,gaussian_blur,jpeg,resolution"
PER_CLASS = "50"
BASELINE, APP_MODEL = "E1_mnv2_frozen_std", "E8_best_ft_qaa_plantdoc"


def step(name: str, cmd: list[str], done) -> None:
    if done():
        print(f"skip {name} (done)", flush=True)
        return
    print(f"$ {name}: {' '.join(cmd[2:])}", flush=True)
    t = time.time()
    with (LOGS / f"analysis_{name}.log").open("a", encoding="utf-8") as log:
        code = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                              env={**os.environ, "KERAS_BACKEND": "torch", "PYTHONUNBUFFERED": "1"}).returncode
    print(f"  exit {code} after {(time.time() - t) / 60:.1f} min", flush=True)
    if code:
        raise SystemExit(code)


def rows_for(family: str, models: list[str]) -> bool:
    path = RESULTS_DIR / "robustness" / f"{family}.csv"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(f"\n{m}," in text for m in models)


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    ev = [PY, "-m", "research.evaluate"]
    step("calibrate", ev + ["calibrate", "--runs", *CNNS],
         lambda: all((RUNS_DIR / r / "calibration.json").exists() for r in CNNS))
    step("robustness_main", ev + ["robustness", "--runs", *MAIN, "--enhance", *ENHANCE, "--per-class", PER_CLASS],
         lambda: rows_for("motion_blur", MAIN + [f"{e}+enh" for e in ENHANCE]))
    for heavy in HEAVY:   # one large model per process: two do not fit in 4 GB together
        step(f"robustness_{heavy[:2]}", ev + ["robustness", "--runs", heavy, "--per-class", PER_CLASS,
                                              "--families", HEAVY_FAMILIES],
             lambda heavy=heavy: rows_for("resolution", [heavy]))
    step("lowlight", ev + ["lowlight", "--runs", BASELINE, "E3_mnv2_ft_qaa", APP_MODEL, "--enhance", BASELINE,
                           "--per-class", PER_CLASS],
         lambda: (RESULTS_DIR / "robustness" / "low_light.csv").exists())
    step("enhance_clean", ev + ["clean", "--runs", "--enhance", *ENHANCE],
         lambda: all((RUNS_DIR / e / "eval" / "pv_test_enh.json").exists() for e in ENHANCE))
    step("enhance_plantdoc", ev + ["plantdoc", "--runs", "--enhance", *ENHANCE],
         lambda: all((RUNS_DIR / e / "eval" / "plantdoc_enh.json").exists() for e in ENHANCE))
    step("export", [PY, "-m", "research.export", "--runs", *CNNS, "--tflite", BASELINE, "E3_mnv2_ft_qaa", APP_MODEL],
         lambda: all((RUNS_DIR / r / "deploy.json").exists() for r in CNNS))
    step("thresholds", [PY, "-m", "research.thresholds", "--model", APP_MODEL, "--compare", BASELINE,
                        "E2_mnv2_ft_std", "E3_mnv2_ft_qaa", "E4_effv2b0_ft_qaa", "--write-app"],
         lambda: (ROOT / "models" / "quality_thresholds.json").exists())
    step("figures", [PY, "-m", "research.figures", "--runs", *CNNS, "--extra", *CLASSICAL,
                     "--enhanced", *ENHANCE, "--baseline", BASELINE, "--best", APP_MODEL],
         lambda: False)
    print("Analysis done.", flush=True)


if __name__ == "__main__":
    main()
