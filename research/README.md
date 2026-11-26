# Research: robustness and cross-dataset study of the leaf disease model

Everything behind the paper's numbers. Each step writes its results to disk and
can be re-run on its own; `research/results/paper/` holds the final figures
and tables (LaTeX + Markdown).

## What is studied

| Question | Where |
| --- | --- |
| How accurate is each model, with confidence intervals? | `evaluate.py clean`, `metrics.py` |
| How do lab-trained models do on field photos (cross-dataset)? | `evaluate.py plantdoc` |
| How do brightness, contrast, noise, blur, JPEG and resolution change accuracy? | `evaluate.py robustness`, `degradations.py` |
| Dark **and** noisy at once (real low light)? | `evaluate.py lowlight` |
| Does quality-aware augmentation (QAA) help, also for unseen defects? | E2 vs E3, `augment.py` |
| Does automatic photo correction help? | `--enhance`, `kisan/disease/enhance.py` |
| What minimum photo quality does the model need? | `thresholds.py` -> `models/quality_thresholds.json` |
| Which backbone is best for a phone (accuracy vs size vs speed)? | `export.py` |
| Are differences between models significant? | McNemar's test in `figures.py` |
| Is there train/test leakage? | `dedup.py` |

## Data

```bash
python scripts/download_data.py --parts 16 --out data/plantvillage_full   # 54,305 files, 38 classes
python scripts/download_plantdoc.py                                      # 2,566 field photos
```

PlantVillage (Hughes & Salathé 2015) has one empty file, skipped, so 54,304
photos are used: 70 / 15 / 15 % stratified split, seed 42 (38,012 / 8,146 /
8,146). PlantDoc (Singh et al. 2020, CC BY 4.0) is only used for testing,
except in E8; 27 of its classes map onto PlantVillage classes
(`PLANTDOC_TO_PV` in `common.py`). Its official test split has 235 photos;
14 of them are exact copies of training photos, several with a different
label, so results are also given on the 221-photo deduplicated test set.

## Environment

TensorFlow has no GPU support on native Windows, so models train with
Keras 3 on the PyTorch backend (CUDA). The data pipeline is tf.data, and
export/TFLite use the TensorFlow backend on the CPU, like the app.

```bash
python -m venv --system-site-packages .venv-gpu      # on a Python that has tensorflow, keras, sklearn, scipy, skimage
.venv-gpu/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv-gpu/Scripts/python -m pip install "opencv-python-headless==4.10.0.84" "numpy==1.26.4"
```

On Colab or Linux with a GPU, plain TensorFlow works: pass `--backend tensorflow`.

## Experiments

| ID | Backbone | Training | Augmentation | Extra data |
| --- | --- | --- | --- | --- |
| E1 | MobileNetV2 | frozen backbone (the app's original recipe) | standard | - |
| E2 | MobileNetV2 | full fine-tuning | standard | - |
| E3 | MobileNetV2 | full fine-tuning | QAA | - |
| E4 | EfficientNetV2-B0 | full fine-tuning | QAA | - |
| E5 | MobileNetV3-Large | full fine-tuning | QAA | - |
| E6 | ResNet50V2 | full fine-tuning | QAA | - |
| E7 | DenseNet121 | full fine-tuning | QAA | - |
| E8 | best of E3-E5 by validation accuracy | full fine-tuning | QAA | PlantDoc train (15% of each batch) |
| C1 | handcrafted colour/texture/HOG features | Random Forest | - | - |
| C2 | same features | RBF SVM (400 photos per class) | - | - |

Fine-tuning: 2 epochs training a new head on the frozen backbone (Adam 1e-3),
then up to 10 epochs on the whole network with BatchNorm statistics frozen,
AdamW (weight decay 0.01), 1 warm-up epoch then cosine decay, label smoothing
0.1, class weights (balanced, capped at 10), mixed precision. The checkpoint
with the best validation accuracy is kept. Test photos are never used for any
choice.

QAA applies, to 70% of training photos, random exposure (x0.25-2.2),
contrast, gamma, colour cast/saturation, Gaussian blur, low resolution,
Gaussian noise (sigma <= 35) and JPEG compression (quality 15-95). Motion blur,
speckle and salt-and-pepper noise are never used in training: they test
robustness to defects the model has not seen.

## Run everything

```bash
python -m research.pipeline                       # E1-E8: train, clean test, PlantDoc (GPU, ~5 h on an RTX 3050 4 GB)
KISAN_WORKERS=4 python -m research.classical --model rf
KISAN_WORKERS=4 python -m research.classical --model svm
python -m research.dedup

python -m research.evaluate clean      --runs C1_rf C2_svm
python -m research.evaluate plantdoc   --runs C1_rf C2_svm
python -m research.evaluate robustness --runs E1_mnv2_frozen_std E2_mnv2_ft_std E3_mnv2_ft_qaa ... --enhance E1_mnv2_frozen_std E3_mnv2_ft_qaa
python -m research.evaluate lowlight   --runs E1_mnv2_frozen_std E3_mnv2_ft_qaa --enhance E1_mnv2_frozen_std
python -m research.export --runs E1_... E2_... --tflite E1_... <best>
python -m research.thresholds --model <app model> --compare E1_mnv2_frozen_std --write-app
python -m research.figures --runs E1_... E2_... E3_... E4_... E5_... E6_... E7_... E8_... \
    --extra C1_rf C2_svm --enhanced E1_mnv2_frozen_std --baseline E1_mnv2_frozen_std --best <best>
```

`research/detach.ps1` starts a long job as a hidden process that keeps running
if the editor is closed (`-Name pipeline -Command "..."`; progress in
`research/logs/<name>.log`, `<name>.status`).

## Metrics

Accuracy, top-3/top-5, macro and weighted precision/recall/F1, balanced
accuracy, Cohen's kappa, MCC, macro one-vs-rest ROC-AUC and PR-AUC, log loss,
Brier score, expected calibration error (15 bins) with reliability diagrams,
the accuracy/coverage trade-off of the app's 70% confidence threshold (and
AURC), 95% bootstrap confidence intervals (1,000 resamples) for accuracy and
macro-F1, and McNemar's test between every pair of models. Robustness:
accuracy per degradation level, mean accuracy over degraded levels (seen and
unseen defect types), relative robustness (corrupted / clean accuracy) and mCE
with the E1 baseline as 100 (Hendrycks & Dietterich 2019).

Cross-dataset results are given two ways: **open set**, where the model
chooses among all 38 classes as in the app, and **restricted**, where it
chooses only among the 27 classes PlantDoc has. Macro averages cover the
classes present in the test set. Also reported: whether the crop was right,
and whether healthy vs diseased was right.

## Image quality measures

`kisan/disease/quality.py` measures, on the 224 x 224 image the model sees:
mean luma (brightness), luma standard deviation (contrast), variance of the
Laplacian (sharpness), Immerkaer's noise sigma per colour channel, shorter
side of the original photo, and the share of clipped highlights/shadows.
`thresholds.py` finds, for each degradation, where accuracy falls more than 5
points below clean accuracy and converts that level into these measured
units. The result is the minimum photo quality reported in the paper, and the
thresholds the app's quality gate uses.

## Tests

```bash
python -m pytest tests/test_research.py
```
