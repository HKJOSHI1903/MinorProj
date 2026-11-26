"""Paper figures and tables from the saved results (no model is run here).

    python -m research.figures --runs E1_mnv2_head_std E2_mnv2_ft_std E3_mnv2_ft_qaa ... \
        --baseline E1_mnv2_head_std --best E3_mnv2_ft_qaa [--extra C1_rf C2_svm]

Writes research/results/paper/: figures as PNG (300 dpi) and PDF, tables as
LaTeX (.tex) and Markdown (.md), and RESULTS.md, which lists every table.

Each model keeps one colour and one marker in every figure (colour follows the
model, never its rank), so figures read in greyscale and for colour-blind readers.
Classical baselines (--extra) are drawn in neutral grey, dashed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from research import degradations as D
from research.common import CACHE_DIR, RESULTS_DIR, RUNS_DIR, read_json

OUT = RESULTS_DIR / "paper"
# Reference categorical palette (light mode), fixed order; validated for adjacent pairs.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
NEUTRAL = "#8a8984"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SEQ_BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

BACKBONE_NAMES = {
    "mobilenetv2": "MobileNetV2", "mobilenetv3large": "MobileNetV3-L", "mobilenetv3small": "MobileNetV3-S",
    "efficientnetb0": "EfficientNet-B0", "efficientnetv2b0": "EfficientNetV2-B0", "efficientnetv2s": "EfficientNetV2-S",
    "resnet50v2": "ResNet50V2", "densenet121": "DenseNet121", "convnexttiny": "ConvNeXt-T", "inceptionv3": "InceptionV3",
}


# ------------------------------------------------------------------ helpers

def style():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "legend.frameon": False, "lines.linewidth": 1.6,
        "lines.markersize": 5,
    })
    return plt


def save(fig, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)
    print(f"  figure {name}")


def label(run: str) -> str:
    cfg_path = RUNS_DIR / run.split("+")[0] / "config.json"
    if not cfg_path.exists():
        return run
    cfg = read_json(cfg_path)
    if str(cfg.get("backbone", "")).startswith("handcrafted"):
        text = "Handcrafted + " + ("Random Forest" if cfg["backbone"].endswith("rf") else "SVM")
    else:
        text = BACKBONE_NAMES.get(cfg["backbone"], cfg["backbone"])
        text += " (frozen)" if cfg.get("fine_tune_epochs", 0) == 0 else " (fine-tuned)"
        if cfg.get("aug") == "robust":
            text += " + QAA"
        if cfg.get("plantdoc_weight", 0) > 0:
            text += " + PlantDoc"
    if "+enh" in run:
        text += " + auto-correct"
    return text


class Styles:
    def __init__(self, runs: list[str], extra: list[str]):
        self.map = {}
        for i, run in enumerate(runs):
            self.map[run] = dict(color=PALETTE[i % 8], marker=MARKERS[i % 8], linestyle="-")
            self.map[f"{run}+enh"] = dict(color=PALETTE[i % 8], marker=MARKERS[i % 8], linestyle=":")
        for i, run in enumerate(extra):
            self.map[run] = dict(color=NEUTRAL, marker=["o", "s", "^"][i % 3], linestyle="--")

    def __call__(self, run):
        return self.map.get(run, dict(color=NEUTRAL, marker="o", linestyle="--"))


def eval_json(run: str, name: str):
    base, enh = run.split("+")[0], "+enh" in run
    path = RUNS_DIR / base / "eval" / f"{name}{'_enh' if enh else ''}.json"
    return read_json(path) if path.exists() else None


def robustness_rows(family: str) -> list[dict]:
    path = RESULTS_DIR / "robustness" / f"{family}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in list(r):
            if k not in ("model", "family", "seen_in_training"):
                r[k] = float(r[k])
    return rows


def pct(x, digits=2):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.{digits}f}"


def write_table(name: str, header: list[str], rows: list[list[str]], caption: str):
    OUT.mkdir(parents=True, exist_ok=True)
    md = [f"**{caption}**", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    (OUT / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    def tex(s: str) -> str:
        return (s.replace("\\", "\\textbackslash{}").replace("%", "\\%").replace("&", "\\&")
                .replace("_", "\\_").replace("#", "\\#").replace("±", "$\\pm$").replace("→", "$\\rightarrow$"))

    lines = ["\\begin{table}[t]", "\\centering", "\\small", f"\\caption{{{tex(caption)}}}",
             f"\\label{{tab:{name}}}", "\\begin{tabular}{l" + "c" * (len(header) - 1) + "}", "\\toprule",
             " & ".join(tex(h) for h in header) + " \\\\", "\\midrule"]
    lines += [" & ".join(tex(c) for c in r) + " \\\\" for r in rows]
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    (OUT / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  table  {name}")
    return "\n".join(md)


# ------------------------------------------------------------------ tables

def table_main(runs):
    rows = []
    for run in runs:
        ev = eval_json(run, "pv_test")
        if not ev:
            continue
        s = ev["summary"]
        dep_path = RUNS_DIR / run.split("+")[0] / "deploy.json"
        dep = read_json(dep_path) if dep_path.exists() else {}
        ci_a, ci_f = s["ci95"]["accuracy"], s["ci95"]["macro_f1"]
        rows.append([label(run),
                     f"{dep['parameters'] / 1e6:.2f}" if dep.get("parameters") else "-",
                     f"{dep['flops'] / 1e9:.2f}" if dep.get("flops") else "-",
                     f"{pct(s['accuracy'])} ({pct(ci_a[0])}–{pct(ci_a[1])})",
                     pct(s["macro_precision"]), pct(s["macro_recall"]),
                     f"{pct(s['macro_f1'])} ({pct(ci_f[0])}–{pct(ci_f[1])})",
                     pct(s["weighted_f1"]), f"{s['cohen_kappa']:.4f}", f"{s['mcc']:.4f}",
                     pct(s["macro_roc_auc"]), f"{s['calibration']['ece']:.4f}", pct(s["top3_accuracy"])])
    return write_table("table_main_comparison",
                       ["Model", "Params (M)", "GFLOPs", "Accuracy % (95% CI)", "Macro-P %", "Macro-R %",
                        "Macro-F1 % (95% CI)", "Weighted-F1 %", "Kappa", "MCC", "Macro ROC-AUC %", "ECE", "Top-3 %"],
                       rows, "Comparison on the PlantVillage test set (38 classes, photos never seen in training)")


def table_cross(runs):
    rows = []
    for run in runs:
        ev = eval_json(run, "plantdoc")
        if not ev:
            continue
        for variant in ("test", "test_dedup"):
            r = ev.get(variant)
            if not r:
                continue
            sel = {row["threshold"]: row for row in r["open_set"]["selective"]["curve"]}
            rows.append([label(run), "deduplicated" if variant == "test_dedup" else "official",
                         str(r["open_set"]["n"]), pct(r["open_set"]["accuracy"]), pct(r["open_set"]["macro_f1"]),
                         pct(r["restricted"]["accuracy"]), pct(r["restricted"]["macro_f1"]),
                         pct(r["crop_accuracy"]), pct(r["healthy_vs_diseased_accuracy"]),
                         pct(sel[0.7]["coverage"], 1), pct(sel[0.7]["accuracy"], 1)])
    return write_table("table_cross_dataset",
                       ["Model", "PlantDoc split", "Photos", "Accuracy %", "Macro-F1 %", "Restricted acc. %",
                        "Restricted macro-F1 %", "Crop correct %", "Healthy vs diseased %",
                        "Answered at 70% conf. %", "Accuracy when answered %"],
                       rows, "Cross-dataset test: trained on PlantVillage (lab), tested on PlantDoc (field photos)")


def corruption_summary(runs, baseline):
    """Mean accuracy over degraded levels per family, mCE relative to the baseline."""
    summary = {run: {"seen": [], "unseen": [], "ce": []} for run in runs}
    clean = {}
    for family, (_fn, _levels, clean_level, _axis, seen) in D.FAMILIES.items():
        rows = robustness_rows(family)
        if not rows:
            continue
        err_base = sum(1 - r["accuracy"] for r in rows if r["model"] == baseline and r["level"] != clean_level)
        for run in runs:
            mine = [r for r in rows if r["model"] == run]
            if not mine:
                continue
            degraded = [r for r in mine if r["level"] != clean_level]
            clean[run] = next((r["accuracy"] for r in mine if r["level"] == clean_level), clean.get(run))
            summary[run]["seen" if seen else "unseen"].append(np.mean([r["accuracy"] for r in degraded]))
            if err_base > 0:
                summary[run]["ce"].append(sum(1 - r["accuracy"] for r in degraded) / err_base)
    return summary, clean


def table_robustness(runs, baseline):
    summary, clean = corruption_summary(runs, baseline)
    req_path = RESULTS_DIR / "quality_requirements.json"
    req = read_json(req_path)["models"] if req_path.exists() else {}
    rows = []
    for run in runs:
        s = summary[run]
        if not (s["seen"] or s["unseen"]):
            continue
        allc = s["seen"] + s["unseen"]
        r = req.get(run, {})
        lo, hi = r.get("brightness_low"), r.get("brightness_high")
        noise = r.get("gaussian_noise_high")
        rows.append([label(run), pct(clean.get(run)), pct(np.mean(s["seen"])) if s["seen"] else "-",
                     pct(np.mean(s["unseen"])) if s["unseen"] else "-",
                     pct(np.mean(allc) / clean[run]) if clean.get(run) else "-",
                     f"{100 * np.mean(s['ce']):.1f}" if s["ce"] else "-",
                     f"{lo['level']:.2f}–{hi['level']:.2f}" if lo and hi else "-",
                     f"{noise['level']:.0f}" if noise else "-"])
    return write_table("table_robustness",
                       ["Model", "Clean acc. %", "Corrupted acc. % (seen types)", "Corrupted acc. % (unseen types)",
                        "Relative robustness %", "mCE (baseline = 100)", "Brightness range (<=5 pt drop)",
                        "Max noise sigma (<=5 pt drop)"],
                       rows, "Robustness to photo degradations (PlantVillage test subset); lower mCE is better")


def table_mcnemar(runs):
    from research.metrics import mcnemar

    out = []
    for name, file in (("PlantVillage test", "pv_test_probs"), ("PlantDoc test", "plantdoc_test_probs")):
        preds = {}
        for run in runs:
            base, enh = run.split("+")[0], "+enh" in run
            path = RUNS_DIR / base / "eval" / f"{file}{'_enh' if enh else ''}.npz"
            if path.exists():
                data = np.load(path)
                preds[run] = (data["y"], data["probs"].astype(np.float32).argmax(1))
        names = list(preds)
        rows = []
        for a in names:
            cells = [label(a)]
            for b in names:
                if a == b:
                    cells.append("–")
                    continue
                ya, pa = preds[a]
                yb, pb = preds[b]
                if len(ya) != len(yb) or not np.array_equal(ya, yb):
                    cells.append("n/a")
                    continue
                t = mcnemar(ya, pa, pb)
                cells.append(f"{t['p_value']:.1e}" + ("*" if t["p_value"] < 0.05 else ""))
            rows.append(cells)
        if rows:
            out.append(write_table(f"table_mcnemar_{'pv' if 'Village' in name else 'plantdoc'}",
                                   ["Model"] + [label(n) for n in names], rows,
                                   f"McNemar's test p-values on the {name} (* = significant at 0.05)"))
    return "\n\n".join(out)


def table_deploy(runs):
    rows = []
    for run in runs:
        path = RUNS_DIR / run / "deploy.json"
        if not path.exists():
            continue
        d = read_json(path)
        rows.append([label(run), "Keras float32", f"{d['keras_file_mb']:.1f}",
                     f"{d['keras_cpu_latency_ms']['median']:.1f}", pct(d["keras_subset_accuracy"]), "100.00"])
        for variant, t in d.get("tflite", {}).items():
            rows.append([label(run), f"TFLite {variant.replace('_', ' ')}", f"{t['file_mb']:.2f}",
                         f"{t['latency_ms']['median']:.1f}", pct(t["subset_accuracy"]),
                         pct(t["agreement_with_float32_keras"])])
    return write_table("table_deployment", ["Model", "Format", "Size (MB)", "CPU latency (ms/photo)",
                                            "Accuracy % (50/class subset)", "Agreement with float32 %"],
                       rows, "Deployment cost: model size, single-photo CPU latency and quantization")


def table_calibration(runs):
    rows = []
    for run in runs:
        path = RUNS_DIR / run / "calibration.json"
        if not path.exists():
            continue
        c = read_json(path)
        cells = [label(run), f"{c['temperature']:.3f}"]
        for name in ("pv_test", "plantdoc_test"):
            b, a = c.get(name, {}).get("before"), c.get(name, {}).get("after")
            if not (b and a):
                cells += ["-"] * 3
                continue
            cells += [f"{b['ece']:.3f} → {a['ece']:.3f}",
                      f"{100 * b['answered_at_0.7']:.0f} → {100 * a['answered_at_0.7']:.0f}",
                      f"{100 * b['accuracy_when_answered']:.1f} → {100 * a['accuracy_when_answered']:.1f}"]
        rows.append(cells)
    return write_table("table_calibration",
                       ["Model", "Temperature", "PV ECE", "PV answered at 0.7 %", "PV acc. when answered %",
                        "PlantDoc ECE", "PlantDoc answered at 0.7 %", "PlantDoc acc. when answered %"],
                       rows, "Temperature scaling fitted on the PlantVillage validation set (before → after): "
                             "it fixes lab calibration but worsens field calibration")


def table_literature():
    path = Path(__file__).with_name("literature.json")
    if not path.exists():
        return ""
    lit = json.loads(path.read_text(encoding="utf-8"))
    rows = [[e["work"], e["model"], e["dataset"], e["protocol"], e["accuracy"], e.get("field_test", "-")]
            for e in lit["entries"]]
    return write_table("table_literature", ["Work", "Model", "Dataset", "Protocol", "Accuracy", "Field / cross-dataset"],
                       rows, lit.get("caption", "Published results (as reported by the authors)"))


def table_quality():
    path = RESULTS_DIR / "quality_requirements.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    (OUT / "table_quality_requirements.md").write_text(text, encoding="utf-8")
    return text


# ------------------------------------------------------------------ figures

def fig_family_grid(runs, styles):
    plt = style()
    fams = list(D.FAMILIES)
    cols = 4
    fig, axes = plt.subplots(math.ceil(len(fams) / cols), cols, figsize=(12, 8.5), sharey=True)
    for ax, family in zip(axes.flat, fams):
        _fn, levels, clean, axis_label, seen = D.FAMILIES[family]
        rows = robustness_rows(family)
        for run in runs:
            mine = sorted((r for r in rows if r["model"] == run), key=lambda r: r["level"])
            if mine:
                ax.plot([r["level"] for r in mine], [100 * r["accuracy"] for r in mine], **styles(run), label=label(run))
        ax.axvline(clean, color=INK2, linewidth=0.8, linestyle="--")
        ax.set_title(family.replace("_", " ").capitalize() + ("" if seen else " (unseen in training)"))
        ax.set_xlabel(axis_label)
        if family in ("brightness", "contrast"):          # factors: always positive
            ax.set_xscale("log")
            ax.set_xticks([0.1, 0.2, 0.5, 1, 2, 3])
            ax.set_xticklabels(["0.1", "0.2", "0.5", "1", "2", "3"])
        elif family in ("speckle", "salt_pepper"):        # start at 0, spread the small amounts
            ax.set_xscale("symlog", linthresh=0.01)
            ax.set_xlim(left=0)
    for ax in axes.flat[len(fams):]:
        ax.axis("off")
    for ax in axes[:, 0]:
        ax.set_ylabel("Accuracy (%)")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    spare = axes.flat[len(fams)] if len(fams) < axes.size else None
    if spare is not None:                                 # the empty last panel holds the legend
        spare.legend(handles, labels, loc="center", fontsize=7.5)
    else:
        fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=7.5)
    fig.tight_layout()
    save(fig, "fig_robustness_all_degradations")


def fig_brightness(runs, styles):
    plt = style()
    rows = robustness_rows("brightness")
    if not rows:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, metric, title in ((axes[0], "accuracy", "Accuracy"), (axes[1], "macro_f1", "Macro F1")):
        for run in runs:
            mine = sorted((r for r in rows if r["model"] == run), key=lambda r: r["level"])
            if mine:
                ax.plot([r["level"] for r in mine], [100 * r[metric] for r in mine], **styles(run), label=label(run))
        ax.axvline(1.0, color=INK2, linewidth=0.8, linestyle="--")
        ax.axvspan(0.25, 2.2, color=GRID, alpha=0.5, linewidth=0, label="QAA training range")
        ax.set_xscale("log")
        ax.set_xticks([0.1, 0.2, 0.3, 0.5, 1, 2, 3])
        ax.set_xticklabels(["0.1", "0.2", "0.3", "0.5", "1", "2", "3"])
        ax.set_xlabel("Brightness factor (1 = original exposure)")
        ax.set_title(title)
    axes[0].set_ylabel("%")
    axes[1].legend(fontsize=7.5, loc="lower center")
    fig.tight_layout()
    save(fig, "fig_brightness_impact")


def fig_noise(runs, styles):
    plt = style()
    fams = [("gaussian_noise", "Gaussian noise sigma (0-255)"), ("salt_pepper", "Salt & pepper share of pixels"),
            ("speckle", "Speckle variance")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    for ax, (family, xlabel) in zip(axes, fams):
        rows = robustness_rows(family)
        for run in runs:
            mine = sorted((r for r in rows if r["model"] == run), key=lambda r: r["level"])
            if mine:
                ax.plot([r["level"] for r in mine], [100 * r["accuracy"] for r in mine], **styles(run), label=label(run))
        ax.set_xlabel(xlabel)
        ax.set_title(family.replace("_", " ").capitalize() + ("" if D.FAMILIES[family][4] else " (unseen)"))
    axes[0].set_ylabel("Accuracy (%)")
    axes[-1].legend(fontsize=7.5)
    fig.tight_layout()
    save(fig, "fig_noise_impact")


def fig_low_light(runs):
    plt = style()
    from matplotlib.colors import LinearSegmentedColormap

    path = RESULTS_DIR / "robustness" / "low_light.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    runs = [r for r in runs if any(row["model"] == r for row in rows)]
    if not runs:
        return
    cmap = LinearSegmentedColormap.from_list("blues", SEQ_BLUES)
    fig, axes = plt.subplots(1, len(runs), figsize=(3.4 * len(runs), 3.4), squeeze=False)
    for ax, run in zip(axes[0], runs):
        grid = np.full((len(D.LOW_LIGHT_BRIGHTNESS), len(D.LOW_LIGHT_NOISE)), np.nan)
        for row in rows:
            if row["model"] == run:
                i = D.LOW_LIGHT_BRIGHTNESS.index(float(row["brightness"]))
                j = D.LOW_LIGHT_NOISE.index(float(row["noise_sigma"]))
                grid[i, j] = 100 * float(row["accuracy"])
        im = ax.imshow(grid, cmap=cmap, vmin=0, vmax=100, origin="lower", aspect="auto")
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                ax.text(j, i, f"{grid[i, j]:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if grid[i, j] > 60 else INK)
        ax.set_xticks(range(len(D.LOW_LIGHT_NOISE)), [str(s) for s in D.LOW_LIGHT_NOISE])
        ax.set_yticks(range(len(D.LOW_LIGHT_BRIGHTNESS)), [str(b) for b in D.LOW_LIGHT_BRIGHTNESS])
        ax.set_xlabel("Noise sigma")
        ax.set_ylabel("Brightness factor")
        ax.set_title(label(run), fontsize=8.5)
        ax.grid(False)
    fig.colorbar(im, ax=axes[0].tolist(), shrink=0.8, label="Accuracy (%)")
    save(fig, "fig_low_light_heatmap")


def fig_reliability_and_coverage(runs, styles):
    plt = style()
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    axes[0].plot([0, 1], [0, 1], color=INK2, linewidth=0.8, linestyle="--")
    for run in runs:
        ev = eval_json(run, "pv_test")
        pd = eval_json(run, "plantdoc")
        if ev:
            rel = ev["summary"]["calibration"]["reliability"]
            axes[0].plot([b["confidence"] for b in rel], [b["accuracy"] for b in rel], **styles(run), label=label(run))
            cur = ev["summary"]["selective"]["curve"]
            axes[1].plot([c["coverage"] * 100 for c in cur], [c["accuracy"] * 100 for c in cur], **styles(run))
        if pd and pd.get("test"):
            cur = pd["test"]["open_set"]["selective"]["curve"]
            axes[2].plot([c["coverage"] * 100 for c in cur], [c["accuracy"] * 100 for c in cur], **styles(run))
            at = next(c for c in cur if c["threshold"] == 0.7)
            axes[2].scatter([at["coverage"] * 100], [at["accuracy"] * 100], s=60, facecolors="none",
                            edgecolors=styles(run)["color"], linewidths=1.5, zorder=5)
    axes[0].set(xlabel="Confidence", ylabel="Accuracy", title="Reliability (PlantVillage test)")
    axes[1].set(xlabel="Photos answered (%)", ylabel="Accuracy when answered (%)",
                title="Confidence threshold (PlantVillage)")
    axes[2].set(xlabel="Photos answered (%)", ylabel="Accuracy when answered (%)",
                title="Confidence threshold (PlantDoc); circle = 0.7")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    save(fig, "fig_calibration_and_threshold")


def fig_training_curves(runs, styles):
    plt = style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for run in runs:
        path = RUNS_DIR / run / "history.json"
        if not path.exists():
            continue
        h = read_json(path)
        epochs = range(1, len(h["val_accuracy"]) + 1)
        axes[0].plot(epochs, [100 * v for v in h["val_accuracy"]], **styles(run), label=label(run))
        axes[1].plot(epochs, h["val_loss"], **styles(run))
    axes[0].set(xlabel="Epoch", ylabel="Validation accuracy (%)", title="Validation accuracy")
    axes[1].set(xlabel="Epoch", ylabel="Validation loss", title="Validation loss")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    save(fig, "fig_training_curves")


def fig_pareto(runs, styles):
    plt = style()
    pts = []
    for run in runs:
        dep_path = RUNS_DIR / run / "deploy.json"
        ev, pd = eval_json(run, "pv_test"), eval_json(run, "plantdoc")
        if dep_path.exists() and ev:
            d = read_json(dep_path)
            pts.append((run, d["keras_cpu_latency_ms"]["median"], d["parameters"],
                        ev["summary"]["accuracy"], pd["test"]["open_set"]["accuracy"] if pd else None))
    if not pts:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for run, lat, params, acc, pd_acc in pts:
        size = 30 + params / 1e5
        axes[0].scatter(lat, 100 * acc, s=size, color=styles(run)["color"], marker=styles(run)["marker"],
                        edgecolors="white", linewidths=1, label=label(run))
        if pd_acc is not None:
            axes[1].scatter(lat, 100 * pd_acc, s=size, color=styles(run)["color"], marker=styles(run)["marker"],
                            edgecolors="white", linewidths=1)
    for ax, title in ((axes[0], "PlantVillage (lab)"), (axes[1], "PlantDoc (field)")):
        ax.set_xscale("log")
        ax.set(xlabel="CPU latency per photo (ms, log scale)", ylabel="Accuracy (%)", title=title)
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    save(fig, "fig_accuracy_vs_latency")


def fig_per_class(baseline, best):
    plt = style()
    for name, key in (("pv", "pv_test"), ("plantdoc", "plantdoc")):
        a, b = eval_json(baseline, key), eval_json(best, key)
        if not (a and b):
            continue
        pa = a["per_class"] if key == "pv_test" else a["test"]["per_class"]
        pb = b["per_class"] if key == "pv_test" else b["test"]["per_class"]
        classes = [r["class"].replace("___", " - ").replace("_", " ") for r in pa]
        fig, ax = plt.subplots(figsize=(7, 0.22 * len(classes) + 1))
        y = np.arange(len(classes))
        ax.barh(y + 0.2, [100 * r["f1"] for r in pa], height=0.38, color=PALETTE[0], label=label(baseline))
        ax.barh(y - 0.2, [100 * r["f1"] for r in pb], height=0.38, color=PALETTE[1], label=label(best))
        ax.set_yticks(y, classes, fontsize=6.5)
        ax.invert_yaxis()
        ax.set_xlabel("F1 (%)")
        ax.set_title(f"Per-class F1, {'PlantVillage test' if name == 'pv' else 'PlantDoc test'}")
        ax.legend(fontsize=7, loc="lower right")
        ax.grid(axis="y", visible=False)
        fig.tight_layout()
        save(fig, f"fig_per_class_f1_{name}")


def fig_confusion(best):
    plt = style()
    from matplotlib.colors import LinearSegmentedColormap
    from sklearn.metrics import confusion_matrix

    cmap = LinearSegmentedColormap.from_list("blues", ["#ffffff"] + SEQ_BLUES)
    meta = read_json(RUNS_DIR / best / "class_names.json")
    names = [n.replace("___", " - ").replace("_", " ") for n in meta["class_names"]]
    for key, title in (("pv_test_probs", "PlantVillage test"), ("plantdoc_test_probs", "PlantDoc test")):
        path = RUNS_DIR / best / "eval" / f"{key}.npz"
        if not path.exists():
            continue
        data = np.load(path)
        y, pred = data["y"], data["probs"].astype(np.float32).argmax(1)
        labels = sorted(set(y.tolist())) if "plantdoc" in key else list(range(len(names)))
        cols = sorted(set(labels) | set(pred.tolist()))
        m = confusion_matrix(y, pred, labels=cols).astype(float)
        rows_idx = [cols.index(c) for c in labels]
        m = m[rows_idx]
        m = 100 * m / np.clip(m.sum(axis=1, keepdims=True), 1, None)
        fig, ax = plt.subplots(figsize=(0.28 * len(cols) + 3, 0.28 * len(labels) + 2))
        ax.imshow(m, cmap=cmap, vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(cols)), [names[c] for c in cols], rotation=90, fontsize=5.5)
        ax.set_yticks(range(len(labels)), [names[c] for c in labels], fontsize=5.5)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(f"{label(best)}: confusion matrix, {title} (row %)", fontsize=9)
        ax.grid(False)
        fig.tight_layout()
        save(fig, f"fig_confusion_{'pv' if 'pv' in key else 'plantdoc'}")


def fig_quality_gap():
    """Measured photo quality of lab (PlantVillage) vs field (PlantDoc) photos, with the gate thresholds."""
    plt = style()
    from kisan.disease.quality import load_thresholds, measure_array

    sets = {}
    for name, cache in (("PlantVillage test", "pv_test_224.npz"), ("PlantDoc test", "plantdoc_test_224.npz")):
        path = CACHE_DIR / cache
        if path.exists():
            x = np.load(path)["x"]
            x = x[:: max(1, len(x) // 1500)]
            sets[name] = [measure_array(im, 224) for im in x]
    if not sets:
        return
    t = load_thresholds.__wrapped__()
    measures = [("brightness", "Brightness (mean luma)", ["min_brightness", "max_brightness"]),
                ("contrast", "Contrast (luma std)", ["min_contrast"]),
                ("sharpness", "Sharpness (Laplacian var.)", ["min_sharpness"]),
                ("noise", "Noise sigma (Immerkaer)", ["max_noise"])]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.2))
    for ax, (key, title, tkeys) in zip(axes, measures):
        for i, (name, rows) in enumerate(sets.items()):
            values = np.array([r[key] for r in rows])
            if key == "sharpness":
                values = np.log10(values + 1)
            ax.hist(values, bins=40, color=PALETTE[i], alpha=0.55, label=name, density=True)
        for tk in tkeys:
            v = t[tk]
            ax.axvline(np.log10(v + 1) if key == "sharpness" else v, color=INK, linewidth=1, linestyle="--")
        ax.set_title(title + (" (log10)" if key == "sharpness" else ""))
        ax.set_yticks([])
    axes[0].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    save(fig, "fig_quality_lab_vs_field")


def fig_degradation_examples():
    plt = style()
    path = CACHE_DIR / "pv_test_224.npz"
    if not path.exists():
        return
    data = np.load(path)
    img = data["x"][len(data["x"]) // 3]
    show = {"brightness": [0.15, 0.4, 1.8, 3.0], "contrast": [0.2, 0.5, 2.0, 3.0],
            "gaussian_noise": [10, 25, 50, 80], "salt_pepper": [0.01, 0.05, 0.1, 0.2],
            "gaussian_blur": [1, 2, 4, 7], "motion_blur": [5, 9, 17, 29], "jpeg": [50, 20, 10, 2],
            "resolution": [96, 48, 32, 16], "color_cast": [-0.5, -0.25, 0.25, 0.5]}
    fig, axes = plt.subplots(len(show), 5, figsize=(7.5, 1.55 * len(show)))
    for row, (family, levels) in zip(axes, show.items()):
        fn = D.FAMILIES[family][0]
        row[0].imshow(img)
        row[0].set_ylabel(family.replace("_", " "), fontsize=7)
        row[0].set_title("original" if family == "brightness" else "", fontsize=7)
        for ax, level in zip(row[1:], levels):
            ax.imshow(fn(img, level, np.random.default_rng(0)))
            ax.set_title(str(level), fontsize=7)
        for ax in row:
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
    fig.tight_layout()
    save(fig, "fig_degradation_examples")


# ------------------------------------------------------------------ main

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--runs", nargs="+", required=True, help="CNN runs in a fixed order (sets their colours)")
    p.add_argument("--extra", nargs="*", default=[], help="classical baselines, drawn in grey")
    p.add_argument("--enhanced", nargs="*", default=[], help="runs also evaluated with auto-correction")
    p.add_argument("--baseline", required=True)
    p.add_argument("--best", required=True)
    args = p.parse_args()

    styles = Styles(args.runs, args.extra)
    everyone = args.runs + [f"{r}+enh" for r in args.enhanced] + args.extra
    tables = [table_main(everyone), table_cross(everyone), table_robustness(everyone, args.baseline),
              table_mcnemar(args.runs + args.extra), table_deploy(args.runs), table_calibration(args.runs),
              table_quality(), table_literature()]

    fig_family_grid(everyone, styles)
    fig_brightness(everyone, styles)
    fig_noise(everyone, styles)
    fig_low_light([args.baseline, args.best] + [f"{r}+enh" for r in args.enhanced][:1])
    fig_reliability_and_coverage(args.runs, styles)
    fig_training_curves(args.runs, styles)
    fig_pareto(args.runs, styles)
    fig_per_class(args.baseline, args.best)
    fig_confusion(args.best)
    fig_quality_gap()
    fig_degradation_examples()

    figures = sorted(p.name for p in OUT.glob("fig_*.png"))
    (OUT / "RESULTS.md").write_text(
        "# Results\n\nGenerated by `python -m research.figures`. Every number comes from research/runs/*/eval "
        "and research/results/.\n\n" + "\n\n".join(t for t in tables if t) +
        "\n\n## Figures\n\n" + "\n".join(f"- ![{f}]({f})" for f in figures) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
