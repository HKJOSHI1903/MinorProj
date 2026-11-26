"""Every number the paper reports, computed from predicted probabilities.

summarize()  accuracy, top-k, macro/weighted precision, recall and F1, balanced
             accuracy, Cohen's kappa, MCC, macro ROC-AUC and PR-AUC, log loss,
             Brier score, calibration error, bootstrap 95% confidence intervals
             and the confidence-threshold (selective prediction) curve.
mcnemar()    are two models' errors on the same photos significantly different?
"""

from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score, cohen_kappa_score,
                             log_loss, matthews_corrcoef, precision_recall_fscore_support,
                             roc_auc_score)

THRESHOLDS = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]


def top_k_accuracy(y, probs, k: int) -> float:
    top = np.argsort(probs, axis=1)[:, ::-1][:, :k]
    return float((top == np.asarray(y)[:, None]).any(axis=1).mean())


def calibration(y, probs, bins: int = 15) -> dict:
    """Expected and maximum calibration error, plus the reliability diagram points."""
    conf = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == y).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    ece, mce, diagram = 0.0, 0.0, []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi)
        if not mask.any():
            continue
        gap = abs(correct[mask].mean() - conf[mask].mean())
        ece += mask.mean() * gap
        mce = max(mce, gap)
        diagram.append({"bin": [float(lo), float(hi)], "confidence": float(conf[mask].mean()),
                        "accuracy": float(correct[mask].mean()), "count": int(mask.sum())})
    return {"ece": float(ece), "mce": float(mce), "reliability": diagram}


def selective(y, probs) -> dict:
    """Answer only when confidence >= t: how many photos are answered and how often correctly.

    The app's threshold is 0.7. AURC (area under the risk-coverage curve) is
    lower for models whose confidence ranks their own mistakes better.
    """
    conf = probs.max(axis=1)
    correct = probs.argmax(axis=1) == y
    rows = []
    for t in THRESHOLDS:
        answered = conf >= t
        rows.append({"threshold": t, "coverage": float(answered.mean()),
                     "accuracy": float(correct[answered].mean()) if answered.any() else float("nan")})
    order = np.argsort(-conf)
    risk = np.cumsum(~correct[order]) / np.arange(1, len(order) + 1)
    return {"curve": rows, "aurc": float(risk.mean())}


def _core(y, pred, labels) -> dict:
    p_ma, r_ma, f_ma, _ = precision_recall_fscore_support(y, pred, labels=labels, average="macro", zero_division=0)
    p_w, r_w, f_w, _ = precision_recall_fscore_support(y, pred, labels=labels, average="weighted", zero_division=0)
    return {"accuracy": float(accuracy_score(y, pred)),
            "macro_precision": float(p_ma), "macro_recall": float(r_ma), "macro_f1": float(f_ma),
            "weighted_precision": float(p_w), "weighted_recall": float(r_w), "weighted_f1": float(f_w)}


def bootstrap_ci(y, pred, labels, n: int = 1000, seed: int = 0) -> dict:
    """95% percentile bootstrap intervals for accuracy and macro F1 (photos resampled with replacement)."""
    rng = np.random.default_rng(seed)
    y, pred = np.asarray(y), np.asarray(pred)
    acc, f1 = [], []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        acc.append((y[idx] == pred[idx]).mean())
        f1.append(precision_recall_fscore_support(y[idx], pred[idx], labels=labels,
                                                  average="macro", zero_division=0)[2])
    return {"accuracy": [float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))],
            "macro_f1": [float(np.percentile(f1, 2.5)), float(np.percentile(f1, 97.5))]}


def summarize(y, probs, labels=None, ci: bool = True, n_boot: int = 1000) -> dict:
    """All metrics. `labels` limits the macro averages to the classes that occur
    (cross-dataset tests only cover some of the 38 classes)."""
    y = np.asarray(y)
    probs = np.asarray(probs, dtype=np.float64)
    pred = probs.argmax(axis=1)
    labels = sorted(set(y.tolist())) if labels is None else list(labels)
    out = _core(y, pred, labels)
    out.update({
        "n": int(len(y)),
        "classes": len(labels),
        "top3_accuracy": top_k_accuracy(y, probs, 3),
        "top5_accuracy": top_k_accuracy(y, probs, 5),
        "balanced_accuracy": out["macro_recall"],
        "cohen_kappa": float(cohen_kappa_score(y, pred)),
        "mcc": float(matthews_corrcoef(y, pred)),
        "log_loss": float(log_loss(y, np.clip(probs, 1e-12, 1), labels=range(probs.shape[1]))),
        "brier": float(((probs - np.eye(probs.shape[1])[y]) ** 2).sum(axis=1).mean()),
        "mean_confidence": float(probs.max(axis=1).mean()),
    })
    present = [c for c in labels if (y == c).any()]
    onehot = np.eye(probs.shape[1])[y][:, present]
    try:
        out["macro_roc_auc"] = float(roc_auc_score(onehot, probs[:, present], average="macro"))
        out["macro_pr_auc"] = float(average_precision_score(onehot, probs[:, present], average="macro"))
    except ValueError:
        out["macro_roc_auc"] = out["macro_pr_auc"] = float("nan")
    out["calibration"] = calibration(y, probs)
    out["selective"] = selective(y, probs)
    if ci:
        out["ci95"] = bootstrap_ci(y, pred, labels, n=n_boot)
    return out


def per_class(y, probs, class_names, labels=None) -> list[dict]:
    y = np.asarray(y)
    pred = np.asarray(probs).argmax(axis=1)
    labels = sorted(set(y.tolist())) if labels is None else list(labels)
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=labels, zero_division=0)
    return [{"class": class_names[c], "precision": float(p[i]), "recall": float(r[i]),
             "f1": float(f[i]), "support": int(s[i])} for i, c in enumerate(labels)]


def fast(y, probs, labels=None) -> dict:
    """Accuracy, macro F1 and mean confidence only (for the robustness sweeps)."""
    y = np.asarray(y)
    pred = np.asarray(probs).argmax(axis=1)
    labels = sorted(set(y.tolist())) if labels is None else list(labels)
    core = _core(y, pred, labels)
    return {"accuracy": core["accuracy"], "macro_f1": core["macro_f1"],
            "mean_confidence": float(np.asarray(probs).max(axis=1).mean()),
            "answered_at_0.7": float((np.asarray(probs).max(axis=1) >= 0.7).mean())}


def mcnemar(y, pred_a, pred_b) -> dict:
    """McNemar's test with continuity correction on paired predictions.

    b = photos A gets right and B gets wrong, c = the reverse. With few
    disagreements (b + c < 25) the exact binomial test is used instead.
    """
    y = np.asarray(y)
    a_ok, b_ok = np.asarray(pred_a) == y, np.asarray(pred_b) == y
    b = int((a_ok & ~b_ok).sum())
    c = int((~a_ok & b_ok).sum())
    if b + c == 0:
        return {"b": b, "c": c, "statistic": 0.0, "p_value": 1.0, "method": "none"}
    if b + c < 25:
        from scipy.stats import binomtest
        return {"b": b, "c": c, "statistic": float(min(b, c)),
                "p_value": float(binomtest(min(b, c), b + c, 0.5).pvalue), "method": "exact"}
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    from scipy.stats import chi2
    return {"b": b, "c": c, "statistic": float(stat), "p_value": float(chi2.sf(stat, 1)),
            "method": "chi2_cc"}


def fmt_ci(value: float, ci: list[float] | None) -> str:
    if not ci or any(math.isnan(v) for v in ci):
        return f"{100 * value:.2f}"
    return f"{100 * value:.2f} [{100 * ci[0]:.2f}, {100 * ci[1]:.2f}]"
