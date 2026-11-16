"""Train the leaf disease classifier with transfer learning (MobileNetV2).

    python -m kisan.disease.train                       # train the new top layer only
    python -m kisan.disease.train --fine-tune-epochs 5  # then fine-tune the last layers

This is the laptop version of notebooks/01_disease_model_colab.ipynb: same
model, same split, same output files.

Step 1 keeps the ImageNet-trained MobileNetV2 frozen and trains a new
classification layer on top. Step 2 (optional, slow without a GPU) unfreezes
the last layers of MobileNetV2 and trains them with a very small learning rate.

Outputs: models/plant_disease.keras, models/class_names.json and, in reports/,
metrics.json, classification_report.txt, training_curves.png, confusion_matrix.png.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
SEED = 42


def list_images(data_dir: Path) -> tuple[list[str], list[int], list[str]]:
    """All image paths with their class index, plus the sorted class names."""
    class_names = sorted(p.name for p in data_dir.iterdir() if p.is_dir())
    paths: list[str] = []
    labels: list[int] = []
    for index, name in enumerate(class_names):
        for file in sorted((data_dir / name).iterdir()):
            if file.suffix.lower() in IMAGE_SUFFIXES:
                paths.append(str(file))
                labels.append(index)
    return paths, labels, class_names


def split(paths, labels):
    """70% train, 15% validation, 15% test, each with the same class mix."""
    from sklearn.model_selection import train_test_split

    train_p, rest_p, train_y, rest_y = train_test_split(
        paths, labels, test_size=0.30, stratify=labels, random_state=SEED)
    val_p, test_p, val_y, test_y = train_test_split(
        rest_p, rest_y, test_size=0.50, stratify=rest_y, random_state=SEED)
    return (train_p, train_y), (val_p, val_y), (test_p, test_y)


def make_dataset(paths, labels, image_size: int, batch_size: int, shuffle: bool):
    import tensorflow as tf

    def load(path, label):
        image = tf.io.decode_image(tf.io.read_file(path), channels=3, expand_animations=False)
        image = tf.image.resize(image, (image_size, image_size))
        image.set_shape((image_size, image_size, 3))
        return image, label

    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if shuffle:
        dataset = dataset.shuffle(len(paths), seed=SEED, reshuffle_each_iteration=True)
    dataset = dataset.map(load, num_parallel_calls=tf.data.AUTOTUNE)
    return dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def build_model(num_classes: int, image_size: int):
    import keras
    from keras import layers

    augment = keras.Sequential(
        [
            layers.RandomFlip("horizontal_and_vertical"),
            layers.RandomRotation(0.15),
            layers.RandomZoom(0.15),
            layers.RandomContrast(0.15),
        ],
        name="augmentation",
    )
    base = keras.applications.MobileNetV2(
        input_shape=(image_size, image_size, 3), include_top=False, weights="imagenet")
    base.trainable = False

    inputs = keras.Input(shape=(image_size, image_size, 3), name="leaf_photo")
    x = augment(inputs)                                    # only active while training
    x = layers.Rescaling(1 / 127.5, offset=-1.0)(x)        # 0..255 -> -1..1, as MobileNetV2 expects
    x = base(x, training=False)                            # keeps BatchNorm statistics fixed
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="disease")(x)
    return keras.Model(inputs, outputs, name="kisan_sahayak_mobilenetv2"), base


def compile_model(model, learning_rate: float) -> None:
    import keras

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )


def save_curves(history: dict[str, list[float]], fine_tune_start: int | None, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    epochs = range(1, len(history["loss"]) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for axis, metric, title in ((axes[0], "accuracy", "Accuracy"), (axes[1], "loss", "Loss")):
        axis.plot(epochs, history[metric], marker="o", label="Training")
        axis.plot(epochs, history[f"val_{metric}"], marker="o", label="Validation")
        if fine_tune_start:
            axis.axvline(fine_tune_start + 0.5, color="grey", linestyle="--", label="Fine-tuning starts")
        axis.set_title(title)
        axis.set_xlabel("Epoch")
        axis.legend()
        axis.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_confusion_matrix(y_true, y_pred, class_names: list[str], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix

    from .labels import parse_label

    names = [parse_label(name).title for name in class_names]
    matrix = confusion_matrix(y_true, y_pred, labels=range(len(class_names)))
    fig, axis = plt.subplots(figsize=(16, 14))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Greens", cbar=False,
                xticklabels=names, yticklabels=names, annot_kws={"size": 6}, ax=axis)
    axis.set_xlabel("Predicted")
    axis.set_ylabel("Actual")
    axis.set_title("Confusion matrix on the test set")
    plt.setp(axis.get_xticklabels(), rotation=90, fontsize=7)
    plt.setp(axis.get_yticklabels(), rotation=0, fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "plantvillage")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--image-size", type=int, default=224, choices=[96, 128, 160, 192, 224])
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=6, help="epochs for the new top layer")
    parser.add_argument("--fine-tune-epochs", type=int, default=0,
                        help="extra epochs with the last MobileNetV2 layers unfrozen")
    parser.add_argument("--fine-tune-layers", type=int, default=30)
    args = parser.parse_args()

    import keras
    from sklearn.metrics import (accuracy_score, classification_report,
                                 precision_recall_fscore_support)
    from sklearn.utils.class_weight import compute_class_weight

    from .labels import parse_label

    keras.utils.set_random_seed(SEED)
    started = time.time()

    paths, labels, class_names = list_images(args.data_dir)
    if not paths:
        raise SystemExit(f"No images in {args.data_dir}. Run `python scripts/download_data.py` first.")
    (train_p, train_y), (val_p, val_y), (test_p, test_y) = split(paths, labels)
    print(f"{len(paths)} images, {len(class_names)} classes: "
          f"{len(train_p)} train / {len(val_p)} validation / {len(test_p)} test")

    train_ds = make_dataset(train_p, train_y, args.image_size, args.batch_size, shuffle=True)
    val_ds = make_dataset(val_p, val_y, args.image_size, args.batch_size, shuffle=False)
    test_ds = make_dataset(test_p, test_y, args.image_size, args.batch_size, shuffle=False)

    # Some classes have 10x more photos than others; weights stop the model ignoring the rare ones.
    weights = compute_class_weight("balanced", classes=np.arange(len(class_names)), y=train_y)
    class_weight = dict(enumerate(weights))

    args.model_dir.mkdir(parents=True, exist_ok=True)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.model_dir / "plant_disease.keras"

    # One checkpoint for both steps, so the file always holds the best epoch overall.
    checkpoint = keras.callbacks.ModelCheckpoint(model_path, monitor="val_accuracy", save_best_only=True)

    def callbacks():
        return [keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3), checkpoint]

    model, base = build_model(len(class_names), args.image_size)
    compile_model(model, 1e-3)
    model.summary(show_trainable=True, expand_nested=False)

    print("\nStep 1: training the new classification layer")
    first = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs,
                      class_weight=class_weight, callbacks=callbacks())
    history = {key: list(map(float, values)) for key, values in first.history.items()}
    fine_tune_start = None

    if args.fine_tune_epochs > 0:
        print(f"\nStep 2: fine-tuning the last {args.fine_tune_layers} MobileNetV2 layers")
        fine_tune_start = len(history["loss"])
        base.trainable = True
        for layer in base.layers[: -args.fine_tune_layers]:
            layer.trainable = False
        compile_model(model, 1e-5)
        second = model.fit(train_ds, validation_data=val_ds, epochs=args.fine_tune_epochs,
                           class_weight=class_weight, callbacks=callbacks())
        for key, values in second.history.items():
            history[key].extend(map(float, values))

    model = keras.models.load_model(model_path)  # the best epoch, not necessarily the last
    (args.model_dir / "class_names.json").write_text(
        json.dumps({"image_size": args.image_size, "class_names": class_names}, indent=2),
        encoding="utf-8")

    print("\nEvaluating on the test set (photos the model has never seen)")
    predicted = np.argmax(model.predict(test_ds), axis=1)
    accuracy = float(accuracy_score(test_y, predicted))
    precision, recall, f1, _ = precision_recall_fscore_support(
        test_y, predicted, average="macro", zero_division=0)
    readable = [parse_label(name).title for name in class_names]
    report = classification_report(test_y, predicted, labels=range(len(class_names)),
                                   target_names=readable, digits=3, zero_division=0)
    print(report)

    (args.reports_dir / "classification_report.txt").write_text(report, encoding="utf-8")
    save_curves(history, fine_tune_start, args.reports_dir / "training_curves.png")
    save_confusion_matrix(test_y, predicted, class_names, args.reports_dir / "confusion_matrix.png")
    (args.reports_dir / "metrics.json").write_text(json.dumps({
        "test_accuracy": accuracy,
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
        "best_val_accuracy": max(history["val_accuracy"]),
        "images": {"total": len(paths), "train": len(train_p), "validation": len(val_p), "test": len(test_p)},
        "classes": len(class_names),
        "image_size": args.image_size,
        "epochs": len(history["loss"]),
        "fine_tune_epochs": args.fine_tune_epochs,
        "training_minutes": round((time.time() - started) / 60, 1),
        "history": history,
    }, indent=2), encoding="utf-8")

    print(f"Test accuracy: {accuracy:.4f}  macro precision: {precision:.4f}  "
          f"macro recall: {recall:.4f}  macro F1: {f1:.4f}")
    print(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()
