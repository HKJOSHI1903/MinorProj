"""Deployment comparison: size, FLOPs, CPU latency and TFLite quantization of each model.

    python -m research.export --runs E3 E4 E5 [--tflite E3]

Runs on the TensorFlow backend (CPU), like the web server and a phone would.
Every model is first rebuilt in float32 (models trained in mixed precision keep
float16 layers otherwise, which are slow on CPU) and saved as model_fp32.keras,
the file the app loads.

For the runs given to --tflite it also writes TFLite models in four precisions
(float32, float16, dynamic-range int8, full int8 with a calibration set) and
reports their size, latency and accuracy on a 50-per-class test subset.

Output: research/runs/<name>/deploy.json, research/runs/<name>/tflite/*.tflite
"""

from __future__ import annotations

import argparse
import os
import time

os.environ["KERAS_BACKEND"] = "tensorflow"
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np  # noqa: E402

from research.common import RUNS_DIR, load_many, pv_splits, read_json, stratified_subset, write_json  # noqa: E402


def float32_model(name: str):
    import keras

    from research.train import build_model

    keras.mixed_precision.set_global_policy("float32")
    run = RUNS_DIR / name
    meta = read_json(run / "class_names.json")
    config = read_json(run / "config.json")
    trained = keras.models.load_model(run / "model.keras", compile=False)
    model, _ = build_model(meta["backbone"], len(meta["class_names"]), meta["image_size"], config.get("dropout", 0.3))
    model.set_weights(trained.get_weights())
    model.save(run / "model_fp32.keras")
    return model


def flops(model) -> int:
    """Floating-point operations of one forward pass (multiply and add counted separately)."""
    import tensorflow as tf
    from tensorflow.python.framework.convert_to_constants import convert_variables_to_constants_v2

    shape = (1,) + tuple(model.input_shape[1:])
    concrete = tf.function(lambda x: model(x, training=False)).get_concrete_function(tf.TensorSpec(shape, tf.float32))
    frozen = convert_variables_to_constants_v2(concrete)
    opts = tf.compat.v1.profiler.ProfileOptionBuilder.float_operation()
    opts["output"] = "none"
    info = tf.compat.v1.profiler.profile(graph=frozen.graph, run_meta=tf.compat.v1.RunMetadata(), cmd="op", options=opts)
    return int(info.total_float_ops)


def latency_ms(fn, x, warmup: int = 5, runs: int = 30) -> dict:
    for _ in range(warmup):
        fn(x)
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        fn(x)
        times.append((time.perf_counter() - t) * 1000)
    return {"mean": float(np.mean(times)), "median": float(np.median(times)), "p95": float(np.percentile(times, 95))}


def tflite_variants(model, run_dir, calib: np.ndarray) -> dict:
    import tensorflow as tf

    saved = run_dir / "saved_model"
    model.export(str(saved), format="tf_saved_model", verbose=False)
    out_dir = run_dir / "tflite"
    out_dir.mkdir(exist_ok=True)

    def representative():
        for image in calib:
            yield [image[None].astype(np.float32)]

    variants = {}
    for name in ("float32", "float16", "dynamic_int8", "full_int8"):
        converter = tf.lite.TFLiteConverter.from_saved_model(str(saved))
        if name != "float32":
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
        if name == "float16":
            converter.target_spec.supported_types = [tf.float16]
        if name == "full_int8":
            converter.representative_dataset = representative
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type = tf.float32
            converter.inference_output_type = tf.float32
        path = out_dir / f"{name}.tflite"
        path.write_bytes(converter.convert())
        variants[name] = path
    return variants


def run_tflite(path, images: np.ndarray, threads: int = 4):
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(path), num_threads=threads)
    interpreter.allocate_tensors()
    inp, out = interpreter.get_input_details()[0], interpreter.get_output_details()[0]

    def one(x):
        interpreter.set_tensor(inp["index"], x)
        interpreter.invoke()
        return interpreter.get_tensor(out["index"])

    probs = np.concatenate([one(im[None].astype(np.float32)) for im in images])
    return probs, latency_ms(one, images[:1].astype(np.float32))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--tflite", nargs="*", default=[])
    args = p.parse_args()

    import tensorflow as tf

    tf.config.threading.set_inter_op_parallelism_threads(1)
    (train, _val, test), class_names = pv_splits()
    sub = stratified_subset(test[1], 50)
    x_test, y_test, _ = load_many([test[0][i] for i in sub], [test[1][i] for i in sub], cache_name="pv_test_50")
    cal = stratified_subset(train[1], 5)
    x_cal, _, _ = load_many([train[0][i] for i in cal], [train[1][i] for i in cal], cache_name="pv_calib_5")

    for name in args.runs:
        run_dir = RUNS_DIR / name
        model = float32_model(name)
        keras_probs = model.predict(x_test.astype(np.float32), batch_size=64, verbose=0)
        report = {
            "parameters": int(model.count_params()),
            "flops": flops(model),
            "keras_file_mb": (run_dir / "model_fp32.keras").stat().st_size / 2**20,
            "keras_cpu_latency_ms": latency_ms(lambda x: model(x, training=False), x_test[:1].astype(np.float32)),
            "keras_subset_accuracy": float((keras_probs.argmax(1) == y_test).mean()),
        }
        if name in args.tflite:
            report["tflite"] = {}
            for variant, path in tflite_variants(model, run_dir, x_cal).items():
                probs, lat = run_tflite(path, x_test)
                report["tflite"][variant] = {
                    "file_mb": path.stat().st_size / 2**20, "latency_ms": lat,
                    "subset_accuracy": float((probs.argmax(1) == y_test).mean()),
                    "agreement_with_float32_keras": float((probs.argmax(1) == keras_probs.argmax(1)).mean())}
                print(f"  {name} {variant:13s} {report['tflite'][variant]['file_mb']:.2f} MB  "
                      f"{lat['median']:.1f} ms  acc {report['tflite'][variant]['subset_accuracy']:.4f}")
        write_json(run_dir / "deploy.json", report)
        print(f"{name}: {report['parameters']:,} params, {report['flops'] / 1e9:.2f} GFLOPs, "
              f"{report['keras_file_mb']:.1f} MB, {report['keras_cpu_latency_ms']['median']:.1f} ms/photo on CPU")


if __name__ == "__main__":
    main()
