"""Train the crop recommendation model.

    python -m kisan.crop.train

Steps
1. Explore the data (EDA): class balance, how each feature differs by crop,
   and how the features relate to each other.
2. Compare four models with 5-fold cross-validation: Decision Tree,
   Random Forest, SVM and XGBoost.
3. Pick the one with the best cross-validated accuracy, train it on the
   training split and test it once on the held-out 20%.
4. Save the model, its metrics and a "profile" of every crop (the range of
   each feature it grows in), which the app uses to explain a recommendation.

Outputs: models/crop_model.joblib, models/crop_profiles.json and, in
reports/crop/, metrics.json, model_comparison.png, confusion_matrix.png,
feature_importance.png, feature_by_crop.png, correlation.png.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
SEED = 42


def build_models() -> dict:
    """The four candidates. SVM needs scaled features, so it gets a scaler in front."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier
    from xgboost import XGBClassifier

    return {
        "Decision Tree": DecisionTreeClassifier(random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1),
        "SVM (RBF kernel)": make_pipeline(StandardScaler(), SVC(kernel="rbf", C=10, probability=True,
                                                               random_state=SEED)),
        "XGBoost": XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                                 random_state=SEED, n_jobs=-1, eval_metric="mlogloss"),
    }


def crop_profiles(data: pd.DataFrame) -> dict:
    """For every crop, the range of each feature in the data (5th to 95th percentile)."""
    profiles = {}
    for crop, rows in data.groupby("label"):
        profiles[crop] = {
            feature: {
                "low": round(float(rows[feature].quantile(0.05)), 2),
                "high": round(float(rows[feature].quantile(0.95)), 2),
                "mean": round(float(rows[feature].mean()), 2),
            }
            for feature in FEATURES
        }
    return profiles


def feature_summary(data: pd.DataFrame) -> dict:
    """Range of each feature over the whole dataset, plus Low / Medium / High presets.

    The presets are the 17th, 50th and 83rd percentiles of the training data. They
    let a farmer who has no soil test pick a rough level; they are not the official
    Soil Health Card thresholds.
    """
    summary = {}
    for feature in FEATURES:
        column = data[feature]
        summary[feature] = {
            "min": round(float(column.min()), 2),
            "max": round(float(column.max()), 2),
            "median": round(float(column.median()), 2),
            "presets": {
                "low": round(float(column.quantile(0.17)), 1),
                "medium": round(float(column.quantile(0.50)), 1),
                "high": round(float(column.quantile(0.83)), 1),
            },
        }
    return summary


def save_eda(data: pd.DataFrame, folder: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    # How each feature differs between crops
    fig, axes = plt.subplots(4, 2, figsize=(16, 18))
    order = sorted(data["label"].unique())
    for axis, feature in zip(axes.flat, FEATURES):
        sns.boxplot(data=data, x="label", y=feature, order=order, ax=axis, color="#86cf1f", fliersize=2)
        axis.set_title(feature)
        axis.set_xlabel("")
        axis.tick_params(axis="x", rotation=75)
    axes.flat[-1].axis("off")
    fig.suptitle("Each feature by crop", fontsize=16)
    fig.tight_layout()
    fig.savefig(folder / "feature_by_crop.png", dpi=130)
    plt.close(fig)

    # How the features relate to each other
    fig, axis = plt.subplots(figsize=(7, 6))
    sns.heatmap(data[FEATURES].corr(), annot=True, fmt=".2f", cmap="Greens", ax=axis)
    axis.set_title("Correlation between features")
    fig.tight_layout()
    fig.savefig(folder / "correlation.png", dpi=130)
    plt.close(fig)


def save_comparison(results: dict, folder: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(results)
    means = [results[name]["cv_accuracy_mean"] for name in names]
    errors = [results[name]["cv_accuracy_std"] for name in names]
    fig, axis = plt.subplots(figsize=(8, 4.5))
    bars = axis.bar(names, means, yerr=errors, capsize=6, color="#2fbf71")
    axis.bar_label(bars, labels=[f"{m:.4f}" for m in means], padding=6)
    axis.set_ylim(min(means) - 0.03, 1.005)
    axis.set_ylabel("5-fold cross-validation accuracy")
    axis.set_title("Model comparison")
    fig.tight_layout()
    fig.savefig(folder / "model_comparison.png", dpi=130)
    plt.close(fig)


def save_confusion(y_true, y_pred, classes: list[str], folder: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix

    matrix = confusion_matrix(y_true, y_pred, labels=range(len(classes)))
    fig, axis = plt.subplots(figsize=(11, 10))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Greens", cbar=False,
                xticklabels=classes, yticklabels=classes, ax=axis)
    axis.set_xlabel("Predicted")
    axis.set_ylabel("Actual")
    axis.set_title("Confusion matrix on the test set")
    plt.setp(axis.get_xticklabels(), rotation=75)
    fig.tight_layout()
    fig.savefig(folder / "confusion_matrix.png", dpi=130)
    plt.close(fig)


def save_importance(importance: dict[str, float], folder: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = sorted(importance, key=importance.get)
    fig, axis = plt.subplots(figsize=(7, 4))
    axis.barh(names, [importance[name] for name in names], color="#2fbf71")
    axis.set_xlabel("Drop in accuracy when the feature is shuffled")
    axis.set_title("Feature importance (permutation)")
    fig.tight_layout()
    fig.savefig(folder / "feature_importance.png", dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "crop" / "Crop_recommendation.csv")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "crop")
    args = parser.parse_args()

    from sklearn.inspection import permutation_importance
    from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
    from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
    from sklearn.preprocessing import LabelEncoder

    if not args.data.exists():
        raise SystemExit(f"{args.data} not found. Run `python scripts/download_crop_data.py` first.")
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    args.model_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. Look at the data ----
    data = pd.read_csv(args.data)
    print(f"{len(data)} rows, {data['label'].nunique()} crops, {int(data.isna().sum().sum())} missing values")
    print(data[FEATURES].describe().round(2).to_string())
    print("Rows per crop:", sorted(set(data["label"].value_counts())))
    save_eda(data, args.reports_dir)

    # Crop names become numbers 0..21 (XGBoost needs numeric labels).
    encoder = LabelEncoder()
    X = data[FEATURES]
    y = encoder.fit_transform(data["label"])
    classes = list(encoder.classes_)

    # 80% to train and compare models, 20% kept aside for the final test.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=SEED)

    # ---- 2. Compare the models with cross-validation ----
    # The training data is cut into 5 parts. Each model is trained 5 times, each
    # time tested on a different part, so its score does not depend on one lucky split.
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    results = {}
    for name, model in build_models().items():
        scores = cross_validate(model, X_train, y_train, cv=folds, scoring=["accuracy", "f1_macro"])
        results[name] = {
            "cv_accuracy_mean": float(scores["test_accuracy"].mean()),
            "cv_accuracy_std": float(scores["test_accuracy"].std()),
            "cv_f1_macro_mean": float(scores["test_f1_macro"].mean()),
            "fit_seconds": float(scores["fit_time"].mean()),
        }
        print(f"{name:18s} accuracy {results[name]['cv_accuracy_mean']:.4f} "
              f"+/- {results[name]['cv_accuracy_std']:.4f}   macro F1 {results[name]['cv_f1_macro_mean']:.4f}")
    save_comparison(results, args.reports_dir)

    # ---- 3. Train the best one and test it once ----
    best_name = max(results, key=lambda name: results[name]["cv_accuracy_mean"])
    print(f"\nBest model: {best_name}")
    model = build_models()[best_name]
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)

    accuracy = float(accuracy_score(y_test, predicted))
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, predicted, average="macro", zero_division=0)
    report = classification_report(y_test, predicted, target_names=classes, digits=3, zero_division=0)
    print(report)
    (args.reports_dir / "classification_report.txt").write_text(report, encoding="utf-8")
    save_confusion(y_test, predicted, classes, args.reports_dir)

    # Which inputs matter most: shuffle one column at a time and see how much accuracy drops.
    permutation = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=SEED, n_jobs=-1)
    importance = {feature: float(value) for feature, value in zip(FEATURES, permutation.importances_mean)}
    save_importance(importance, args.reports_dir)

    # ---- 4. Save everything the app needs ----
    joblib.dump({"model": model, "classes": classes, "features": FEATURES, "name": best_name},
                args.model_dir / "crop_model.joblib")
    (args.model_dir / "crop_profiles.json").write_text(json.dumps({
        "features": feature_summary(data),
        "crops": crop_profiles(data),
    }, indent=2), encoding="utf-8")
    (args.reports_dir / "metrics.json").write_text(json.dumps({
        "best_model": best_name,
        "test_accuracy": accuracy,
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
        "rows": {"total": len(data), "train": len(X_train), "test": len(X_test)},
        "crops": len(classes),
        "cross_validation": results,
        "feature_importance": importance,
    }, indent=2), encoding="utf-8")

    print(f"Test accuracy: {accuracy:.4f}  macro precision: {precision:.4f}  "
          f"macro recall: {recall:.4f}  macro F1: {f1:.4f}")
    print(f"Model saved to {args.model_dir / 'crop_model.joblib'}")


if __name__ == "__main__":
    main()
