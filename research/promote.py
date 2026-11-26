"""Make a research model the one the app uses.

    python -m research.promote --run E3_mnv2_ft_qaa

Copies the run's float32 model (written by research/export.py) to
models/plant_disease.keras with models/class_names.json, and rewrites the
app's reports (reports/metrics.json, classification_report.txt,
confusion_matrix.png, training_curves.png) from that run's test-set
evaluation, so the website shows the numbers of the model in use. The
previous files stay in git history.
"""

from __future__ import annotations

import argparse
import json
import shutil

import numpy as np

from research.common import ROOT, RUNS_DIR, read_json, write_json


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--run", required=True)
    p.add_argument("--use-temperature", action="store_true",
                   help="apply the run's validation temperature (makes field-photo confidence worse; see code)")
    args = p.parse_args()

    run = RUNS_DIR / args.run
    fp32 = run / "model_fp32.keras"
    if not fp32.exists():
        raise SystemExit(f"{fp32} is missing: run `python -m research.export --runs {args.run}` first")
    config, meta = read_json(run / "config.json"), read_json(run / "class_names.json")
    evaluation = read_json(run / "eval" / "pv_test.json")
    summary = evaluation["summary"]
    history = read_json(run / "history.json")

    models, reports = ROOT / "models", ROOT / "reports"
    shutil.copyfile(fp32, models / "plant_disease.keras")
    # Temperature scaling fitted on PlantVillage fixes lab calibration but makes field photos
    # (PlantDoc) worse calibrated: the models are overconfident out of domain, and the slight
    # underconfidence left by label smoothing is a safety margin for the 70% warning. So it is
    # only applied when asked for.
    calibration = run / "calibration.json"
    temperature = 1.0
    if args.use_temperature and calibration.exists():
        temperature = read_json(calibration)["temperature"]
    (models / "class_names.json").write_text(json.dumps(
        {"image_size": meta["image_size"], "temperature": round(temperature, 4),
         "class_names": meta["class_names"]}, indent=2), encoding="utf-8")

    n_test = summary["n"]
    write_json(reports / "metrics.json", {
        "test_accuracy": summary["accuracy"],
        "macro_precision": summary["macro_precision"],
        "macro_recall": summary["macro_recall"],
        "macro_f1": summary["macro_f1"],
        "best_val_accuracy": config["best_val_accuracy"],
        "images": {"total": config["train_images"] + config["val_images"] + n_test,
                   "train": config["train_images"], "validation": config["val_images"], "test": n_test},
        "classes": len(meta["class_names"]),
        "image_size": meta["image_size"],
        "epochs": len(history["loss"]),
        "fine_tune_epochs": config.get("fine_tune_epochs", 0),
        "training_minutes": config.get("training_minutes"),
        "model": f"{meta['backbone']} ({args.run})",
        "ci95": summary["ci95"],
        "history": {k: history[k] for k in ("accuracy", "loss", "val_accuracy", "val_loss") if k in history},
    })

    from sklearn.metrics import classification_report

    from kisan.disease.labels import parse_label
    from kisan.disease.train import save_confusion_matrix, save_curves

    data = np.load(run / "eval" / "pv_test_probs.npz")
    y, pred = data["y"], data["probs"].astype(np.float32).argmax(1)
    names = meta["class_names"]
    report = classification_report(y, pred, labels=range(len(names)),
                                   target_names=[parse_label(n).title for n in names], digits=3, zero_division=0)
    (reports / "classification_report.txt").write_text(report, encoding="utf-8")
    save_confusion_matrix(y, pred, names, reports / "confusion_matrix.png")
    head = config.get("head_epochs_done") if config.get("fine_tune_epochs") else None
    save_curves({k: history[k] for k in ("accuracy", "loss", "val_accuracy", "val_loss")}, head,
                reports / "training_curves.png")
    print(f"The app now uses {args.run}: test accuracy {summary['accuracy']:.4f}, macro F1 {summary['macro_f1']:.4f}")


if __name__ == "__main__":
    main()
