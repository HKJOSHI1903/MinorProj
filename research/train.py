"""Train one model for the paper's comparison.

    python -m research.train --name E3_mnv2_ft_qaa --backbone mobilenetv2 --aug robust

Runs on either Keras backend: `--backend torch` uses the GPU on Windows (PyTorch
CUDA), `--backend tensorflow` the CPU. The data pipeline is tf.data in both cases.

Step 1 trains a new classification head on the frozen ImageNet backbone.
Step 2 (`--fine-tune-epochs` > 0) unfreezes the backbone (BatchNorm statistics
stay frozen) and trains everything with AdamW, label smoothing and a
warm-up + cosine learning-rate schedule. The checkpoint with the best
validation accuracy is kept; the test photos are never looked at here.

Output: research/runs/<name>/ with model.keras, config.json, history.json.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--name", required=True)
    p.add_argument("--backbone", default="mobilenetv2")
    p.add_argument("--aug", choices=["standard", "robust"], default="robust")
    p.add_argument("--plantdoc-weight", type=float, default=0.0,
                   help="share of each batch drawn from PlantDoc train (0 = PlantVillage only)")
    p.add_argument("--head-epochs", type=int, default=2)
    p.add_argument("--fine-tune-epochs", type=int, default=10)
    p.add_argument("--fine-tune-layers", type=int, default=0, help="0 = unfreeze the whole backbone")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=2e-4, help="peak fine-tuning learning rate")
    p.add_argument("--label-smoothing", type=float, default=0.1)
    p.add_argument("--dropout", type=float, default=0.3)
    p.add_argument("--image-size", type=int, default=224)
    p.add_argument("--backend", choices=["torch", "tensorflow", "jax"], default=os.environ.get("KERAS_BACKEND", "torch"))
    p.add_argument("--precision", choices=["float32", "mixed_float16", "mixed_bfloat16"], default="mixed_float16")
    p.add_argument("--limit", type=int, default=0, help="debug: use only this many training photos")
    p.add_argument("--init-from", default="",
                   help="start from the weights of this .keras file (e.g. a finished head-training step)")
    return p.parse_args(argv)


ARGS = parse_args() if __name__ == "__main__" else None
if ARGS is not None:
    os.environ["KERAS_BACKEND"] = ARGS.backend
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402

from research.common import RUNS_DIR, SEED, plantdoc_images, pv_splits, write_json  # noqa: E402

# tf.data only: keep TensorFlow off the GPU so PyTorch has all of its memory.
try:
    tf.config.set_visible_devices([], "GPU")
except (RuntimeError, ValueError):
    pass

# name -> (constructor name in keras.applications, input scaling the backbone expects)
BACKBONES = {
    "mobilenetv2": ("MobileNetV2", "minus1to1"),
    "mobilenetv3large": ("MobileNetV3Large", "builtin"),
    "mobilenetv3small": ("MobileNetV3Small", "builtin"),
    "efficientnetb0": ("EfficientNetB0", "builtin"),
    "efficientnetv2b0": ("EfficientNetV2B0", "builtin"),
    "efficientnetv2s": ("EfficientNetV2S", "builtin"),
    "resnet50v2": ("ResNet50V2", "minus1to1"),
    "densenet121": ("DenseNet121", "imagenet_mean_std"),
    "convnexttiny": ("ConvNeXtTiny", "builtin"),
    "inceptionv3": ("InceptionV3", "minus1to1"),
}


def build_model(backbone: str, num_classes: int, image_size: int, dropout: float):
    """0..255 RGB in, softmax out. All scaling is inside the model, so the app feeds raw pixels."""
    import keras
    from keras import layers

    ctor_name, scaling = BACKBONES[backbone]
    ctor = getattr(keras.applications, ctor_name)
    kwargs = dict(input_shape=(image_size, image_size, 3), include_top=False, weights="imagenet")
    base = ctor(**kwargs)
    base.trainable = False

    inputs = keras.Input(shape=(image_size, image_size, 3), name="leaf_photo")
    x = inputs
    if scaling == "minus1to1":
        x = layers.Rescaling(1 / 127.5, offset=-1.0, name="scale")(x)
    elif scaling == "imagenet_mean_std":
        x = layers.Rescaling(1 / 255.0, name="scale")(x)
        x = layers.Normalization(mean=[0.485, 0.456, 0.406],
                                 variance=[0.229 ** 2, 0.224 ** 2, 0.225 ** 2], name="imagenet_norm")(x)
    x = base(x, training=False)                 # BatchNorm stays in inference mode, also when unfrozen
    x = layers.GlobalAveragePooling2D(name="pool")(x)
    x = layers.Dropout(dropout, name="dropout")(x)
    outputs = layers.Dense(num_classes, activation="softmax", dtype="float32", name="disease")(x)
    return keras.Model(inputs, outputs, name=f"kisan_{backbone}"), base


def make_dataset(paths, labels, num_classes, class_weights, image_size, batch_size,
                 training: bool, robust: bool, images=None):
    """tf.data pipeline yielding (image 0..255, one-hot label, sample weight)."""
    from research.augment import geometric, quality_aware

    weights = tf.constant(class_weights, tf.float32)

    def load(path, label):
        raw = tf.io.read_file(path)
        image = tf.io.decode_image(raw, channels=3, expand_animations=False)
        image = tf.image.resize(image, (image_size, image_size), method="bilinear", antialias=True)
        image.set_shape((image_size, image_size, 3))
        return image, label

    def from_array(image, label):
        return tf.cast(image, tf.float32), label

    if images is not None:
        ds = tf.data.Dataset.from_tensor_slices((images, np.asarray(labels, np.int32))).map(from_array)
    else:
        ds = tf.data.Dataset.from_tensor_slices((list(paths), np.asarray(labels, np.int32)))
    if training:
        ds = ds.shuffle(len(labels), seed=SEED, reshuffle_each_iteration=True)
    if images is None:
        ds = ds.map(load, num_parallel_calls=tf.data.AUTOTUNE)

    if training:
        geo = geometric(robust)

        def augment(image, label):
            image = geo(image, training=True)
            if robust:
                image = quality_aware(image)
            return image, label

        ds = ds.map(augment, num_parallel_calls=tf.data.AUTOTUNE)

    def finish(image, label):
        return image, tf.one_hot(label, num_classes), tf.gather(weights, label)

    return ds.map(finish, num_parallel_calls=tf.data.AUTOTUNE)


class EpochTimer:
    def __init__(self):
        import keras

        class _Timer(keras.callbacks.Callback):
            def on_epoch_begin(self, epoch, logs=None):
                self.t = time.time()

            def on_epoch_end(self, epoch, logs=None):
                if logs is not None:
                    logs["epoch_seconds"] = time.time() - self.t

        self.callback = _Timer()


def main(args) -> None:
    import keras
    from sklearn.utils.class_weight import compute_class_weight

    keras.utils.set_random_seed(SEED)
    if args.precision != "float32":
        keras.mixed_precision.set_global_policy(args.precision)
    if keras.backend.backend() == "torch":
        import torch

        if torch.cuda.is_available():
            # On Windows the driver silently moves CUDA memory beyond the card into system RAM
            # (very slow) instead of failing, so PyTorch's cache never stops growing. A cap makes
            # the allocator reuse its cache first.
            torch.cuda.set_per_process_memory_fraction(0.8)

    (train, val, _test), class_names = pv_splits()
    train_p, train_y = train
    val_p, val_y = val
    if args.limit:
        rng = np.random.default_rng(SEED)
        keep = np.sort(rng.choice(len(train_p), args.limit, replace=False))
        train_p, train_y = [train_p[i] for i in keep], [train_y[i] for i in keep]
    n_classes = len(class_names)

    # Balanced weights, capped so the rarest class (Potato healthy) does not dominate.
    cw = compute_class_weight("balanced", classes=np.arange(n_classes), y=train_y)
    cw = np.minimum(cw, 10.0).astype("float32")

    robust = args.aug == "robust"
    train_ds = make_dataset(train_p, train_y, n_classes, cw, args.image_size, args.batch_size, True, robust)
    n_train = len(train_p)
    if args.plantdoc_weight > 0:
        from research.common import load_many

        pd_p, pd_y, _ = plantdoc_images("train", class_names)
        pd_x, pd_y, _ = load_many(pd_p, pd_y, args.image_size, cache_name="plantdoc_train")
        pd_ds = make_dataset(None, pd_y, n_classes, cw, args.image_size, args.batch_size, True, robust,
                             images=pd_x).repeat()
        w = args.plantdoc_weight
        train_ds = tf.data.Dataset.sample_from_datasets([train_ds, pd_ds], weights=[1 - w, w],
                                                        seed=SEED, stop_on_empty_dataset=True)
        n_train = int(n_train / (1 - w))
        print(f"Mixing in {len(pd_y)} PlantDoc train photos at {w:.0%} of each batch")
    train_ds = train_ds.batch(args.batch_size).prefetch(tf.data.AUTOTUNE)
    val_ds = make_dataset(val_p, val_y, n_classes, cw, args.image_size, args.batch_size, False, False)
    # Validation batch: twice the training batch (at most 64) keeps big backbones within GPU memory.
    val_ds = val_ds.map(lambda x, y, w: (x, y)).batch(min(64, 2 * args.batch_size)).prefetch(tf.data.AUTOTUNE)
    steps = math.ceil(n_train / args.batch_size)

    run_dir = RUNS_DIR / args.name
    run_dir.mkdir(parents=True, exist_ok=True)
    model_path = run_dir / "model.keras"
    config = {**vars(args), "classes": n_classes, "train_images": len(train_p), "val_images": len(val_p),
              "keras": keras.__version__, "backend": keras.backend.backend(), "started": time.ctime()}
    write_json(run_dir / "config.json", config)
    (run_dir / "class_names.json").write_text(json.dumps(
        {"image_size": args.image_size, "class_names": class_names, "backbone": args.backbone}, indent=2),
        encoding="utf-8")

    model, base = build_model(args.backbone, n_classes, args.image_size, args.dropout)
    if args.init_from:
        model.set_weights(keras.models.load_model(args.init_from, compile=False).get_weights())
        print(f"Starting from the weights in {args.init_from}")
    print(f"{args.name}: {args.backbone}, {model.count_params():,} parameters, "
          f"{n_train} training photos per epoch, aug={args.aug}, backend={keras.backend.backend()}")

    checkpoint = keras.callbacks.ModelCheckpoint(model_path, monitor="val_accuracy", save_best_only=True)
    loss = keras.losses.CategoricalCrossentropy(label_smoothing=args.label_smoothing)
    metrics = ["accuracy", keras.metrics.TopKCategoricalAccuracy(3, name="top3")]
    history: dict[str, list[float]] = {}
    started = time.time()

    def run(epochs, optimizer, extra=()):
        model.compile(optimizer=optimizer, loss=loss, metrics=metrics)
        result = model.fit(train_ds, validation_data=val_ds, epochs=epochs, steps_per_epoch=None,
                           callbacks=[checkpoint, EpochTimer().callback, *extra], verbose=2)
        for key, values in result.history.items():
            history.setdefault(key, []).extend(float(v) for v in values)

    if args.head_epochs > 0:
        print("\nStep 1: new classification head, backbone frozen")
        run(args.head_epochs, keras.optimizers.Adam(1e-3))
    head_epochs_done = len(history.get("loss", []))

    if args.fine_tune_epochs > 0:
        print(f"\nStep 2: fine-tuning {'the whole backbone' if not args.fine_tune_layers else f'the last {args.fine_tune_layers} layers'}")
        base.trainable = True
        if args.fine_tune_layers:
            for layer in base.layers[: -args.fine_tune_layers]:
                layer.trainable = False
        for layer in base.layers:                     # BatchNorm statistics stay as learned on ImageNet
            if isinstance(layer, keras.layers.BatchNormalization):
                layer.trainable = False
        total = steps * args.fine_tune_epochs
        schedule = keras.optimizers.schedules.CosineDecay(
            initial_learning_rate=args.lr / 20, decay_steps=max(1, total - steps), alpha=0.01,
            warmup_target=args.lr, warmup_steps=steps)
        run(args.fine_tune_epochs, keras.optimizers.AdamW(schedule, weight_decay=0.01),
            extra=[keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=4)])

    config.update({"finished": time.ctime(), "training_minutes": round((time.time() - started) / 60, 1),
                   "parameters": int(model.count_params()), "head_epochs_done": head_epochs_done,
                   "best_val_accuracy": max(history["val_accuracy"])})
    write_json(run_dir / "config.json", config)
    write_json(run_dir / "history.json", history)
    print(f"\nBest validation accuracy {config['best_val_accuracy']:.4f}; model in {model_path}")


if __name__ == "__main__":
    sys.exit(main(ARGS))
