# From Lab to Field: Quality-Aware Training and Minimum Image-Quality Requirements for Smartphone Leaf Disease Diagnosis

*Draft. Every number comes from `research/results/` and `research/runs/*/eval/`; regenerate the tables with `python -m research.figures`.*

## Abstract

Leaf-disease classifiers trained on the PlantVillage dataset routinely report 99% accuracy, yet
farmers' photos are taken in fields, often in poor light, out of focus or from too far away. We
compare eight CNN configurations (MobileNetV2, MobileNetV3-Large, EfficientNetV2-B0, ResNet50V2,
DenseNet121) and two handcrafted-feature baselines on one fixed split of 54,304 PlantVillage
photos, test them on PlantDoc field photos, and measure their accuracy under 116 levels of 11
image degradations, including three never seen in training. We propose quality-aware augmentation
(QAA), a camera-pipeline-ordered chain of exposure, contrast, colour, blur, resolution, noise and
compression defects. All PlantVillage-only models lose 61-71 points on field photos (27-38%
accuracy); handcrafted features fall to chance despite 94% in the lab. QAA costs 0.6 points of lab
accuracy but raises field accuracy by 7.7 points (p = 0.007) and cuts the mean corruption error to
19% of the baseline for MobileNetV2 and 8.5% for EfficientNetV2-B0, holding 95-99% accuracy from
one tenth to twice the normal exposure and up to noise sigma 30, where models without QAA fall to
25%. Adding PlantDoc training photos raises field accuracy to 63.8% (65.6% on a deduplicated test
set) while keeping 99.5% on PlantVillage. Field photos are not of lower measured quality than lab photos, so the gap
stems mainly from scene content. Temperature scaling fitted on lab data improves lab calibration but makes
field predictions more overconfident. From the degradation curves we derive the minimum image
quality each model needs, in measurable units: the deployed model tolerates brightness 12-236,
noise up to 43 and leaves down to 30 px, against 70-201, 4.6 and 91 px for the original
frozen-backbone model. These limits drive a quality gate that tells farmers how to retake a bad
photo. The deployed model runs in 5 ms per photo and 7 MB as an int8 TFLite model.

## 1. Introduction

Smartphone apps that name a crop disease from a photo of one leaf could reach farmers who have no
plant pathologist nearby. Most published classifiers are trained and tested on PlantVillage, a set
of about 54,000 leaf photos taken in a lab on plain backgrounds, where convolutional networks reach
99% accuracy [1]. The same networks lose most of that accuracy on photos taken in fields and
gardens [1, 2], and PlantVillage itself carries capture bias that a model can exploit without
looking at the disease [3]. A farmer's photo is also often dark, blurred, grainy, compressed by a
messaging app or taken from too far away.

This paper studies how a lightweight leaf-disease classifier behaves outside the lab, and what can
be done about it within the budget of a phone app. Its contributions are:

1. **A controlled comparison** of eight CNN configurations (five backbones; frozen vs fine-tuned;
   standard vs quality-aware augmentation; with and without field photos) and two classical
   handcrafted-feature baselines, all on one fixed split, with 95% bootstrap confidence intervals,
   McNemar's tests, calibration and selective-prediction analysis.
2. **A cross-dataset evaluation** on PlantDoc field photos [2], including a duplicate audit of
   PlantDoc's official split (14 of its 235 test photos also appear in its training set, several
   with a different label).
3. **A photo-quality robustness study**: accuracy as a function of brightness, contrast, gamma,
   colour cast, Gaussian / salt-and-pepper / speckle noise, Gaussian and motion blur, JPEG
   compression and resolution, plus a joint low-light (dark + noisy) grid, with three corruption
   types held out from training to test robustness to unseen defects.
4. **Quality-aware augmentation (QAA)**: a camera-pipeline-ordered augmentation of photo defects,
   and its effect on lab, field and degraded photos.
5. **Minimum image-quality requirements** derived from the degradation curves and expressed in
   measurable units (brightness, contrast, sharpness, noise, resolution), deployed as a quality
   gate that tells the farmer how to retake a bad photo.
6. **Deployment measurements**: parameters, FLOPs, CPU latency and TFLite float16 / int8
   quantization of every model.

## 2. Related work

**Lab datasets.** Mohanty et al. [1] trained AlexNet and GoogLeNet on PlantVillage (54,306 photos,
38 classes) and reached 99.35% accuracy with transfer learning on an 80/20 split; on 121 web photos
taken in other conditions the same model scored 31.40% (47.93% when the crop was given). Many later
papers report 99%+ on PlantVillage with deeper or lighter networks.

**Field data.** Singh et al. [2] released PlantDoc, 2,598 field photos in 27 classes overlapping
PlantVillage. A VGG16 trained on PlantVillage reached 15.08% on uncropped PlantDoc photos, and
29.73% after fine-tuning on PlantDoc; on cropped single leaves, InceptionResNetV2 with PlantVillage
pre-training and PlantDoc fine-tuning reached 70.53%. Their images were resized to 100 x 100 px and
split 80/20 by the authors, not with the repository's train/test folders used here.

**Dataset bias.** Noyan [3] showed that a classifier using only 8 background pixels of each
PlantVillage photo reaches 49.0% accuracy (2.6% by chance), so PlantVillage contains
label-correlated capture conditions that inflate in-dataset accuracy.

**Robustness to image quality.** Hendrycks and Dietterich [4] introduced corruption benchmarks and
the mean corruption error (mCE); Dodge and Karam [5] showed that blur and noise degrade CNN accuracy
much more than contrast or JPEG compression. Temperature scaling [6] is a standard post-hoc fix for
miscalibrated confidence.

## 3. Data

**PlantVillage** (colour version) [7]: 54,305 files in 38 classes (14 crops). One file is empty
and is skipped, leaving 54,304 photos, split 70 / 15 / 15% with stratification and a fixed seed
(42): 38,012 training, 8,146 validation, 8,146 test photos. Classes range from 152 to 5,507 photos.
A perceptual-hash audit (64-bit dHash, Hamming distance <= 4) found 59 test photos (0.72%) with a
near-duplicate in the training set, 47 with the same label: consecutive shots of the same leaf.

**PlantDoc** [2]: the repository's train (2,331 photos) and test (235 photos) folders. 27 of its
classes map onto PlantVillage classes (Table A1). PlantDoc is used only for testing, except in
experiment E8, which adds PlantDoc's training photos. 14 test photos are byte-identical or
near-identical to training photos; several carry a different disease label (e.g. "Corn gray leaf
spot" in test and "Corn leaf blight" in train), which indicates label noise. Results are reported
on the official test set (235) and on a deduplicated test set (221).

All photos are resized to 224 x 224 px (bilinear, no crop), exactly as the deployed app does.

## 4. Methods

### 4.1 Models

All CNNs take 0-255 RGB input; each backbone's own input scaling is part of the model. Every model
has an ImageNet-pre-trained backbone, global average pooling, dropout 0.3 and a 38-way softmax.

| ID | Backbone | Params | Training | Augmentation | Extra data |
| --- | --- | --- | --- | --- | --- |
| E1 | MobileNetV2 | 2.31 M | frozen backbone, 6 epochs | standard | - |
| E2 | MobileNetV2 | 2.31 M | full fine-tuning | standard | - |
| E3 | MobileNetV2 | 2.31 M | full fine-tuning | QAA | - |
| E4 | EfficientNetV2-B0 | 5.97 M | full fine-tuning | QAA | - |
| E5 | MobileNetV3-Large | 3.03 M | full fine-tuning | QAA | - |
| E6 | ResNet50V2 | 23.64 M | full fine-tuning | QAA | - |
| E7 | DenseNet121 | 7.08 M | full fine-tuning | QAA | - |
| E8 | EfficientNetV2-B0 | 5.97 M | full fine-tuning | QAA | PlantDoc train |
| C1 | handcrafted features | - | Random Forest (500 trees) | - | - |
| C2 | handcrafted features | - | RBF SVM (C = 10, 400 photos/class) | - | - |

E1 reproduces the recipe of the original app. E8's backbone was fixed in advance by a rule that
uses no test data: the mobile backbone (E3-E5) with the highest PlantVillage validation accuracy.

**Classical features** (446 per photo, on a 128 x 128 copy): HSV histograms (32/16/16 bins), mean,
standard deviation and skewness of the R, G, B, H, S, V channels, uniform LBP histograms at radii
1 and 2, six GLCM statistics at distances 1 and 3, and HOG on a 64 x 64 copy.

### 4.2 Training

Fine-tuned models: 2 epochs training the new head on the frozen backbone (Adam, 1e-3), then up to
10 epochs on the whole network (BatchNorm statistics frozen) with AdamW (weight decay 0.01), one
warm-up epoch followed by cosine decay from a peak of 2-3 x 10^-4, categorical cross-entropy with
label smoothing 0.1, class weights (balanced, capped at 10) and mixed precision. Early stopping
(patience 4) and the checkpoint with the best validation accuracy; the test set is never used for
any choice. Batch sizes are the largest that fit in 4 GB of GPU memory (MobileNetV2 64,
EfficientNetV2-B0 48, MobileNetV3-L 32). The two large reference models were fine-tuned for 4
epochs at batch size 8 (peak learning rate 7 x 10^-5): ResNet50V2's head step ran at batch 16 and
its fine-tuning was resumed from that checkpoint after the batch-16 run was found to exceed GPU
memory. In E8, 15% of every batch comes from PlantDoc's training photos.

Hardware: one NVIDIA RTX 3050 Laptop GPU (4 GB), Keras 3.11 on PyTorch 2.14 (CUDA 12.6); data
pipeline in tf.data on an 8-core AMD Ryzen 7 6800H.

### 4.3 Quality-aware augmentation (QAA)

Standard augmentation (E1, E2): random flips, rotation (+-27 deg), zoom (+-15%) and contrast
(+-15%). QAA (E3-E8) keeps the geometry, adds translation, and applies to 70% of photos a chain of
defects in the order a camera produces them, each with its own probability:

| Step | Range | p |
| --- | --- | --- |
| exposure (multiplicative) | x0.25 - x2.2, log-uniform | 0.5 |
| contrast | x0.4 - x1.8 | 0.4 |
| gamma | 0.5 - 2.0 | 0.2 |
| white balance and saturation | R/B gain +-25%, saturation x0.6 - x1.4 | 0.3 |
| Gaussian blur | sigma 0.3 - 2.5 px | 0.2 |
| low resolution | down to 40 - 200 px and back | 0.2 |
| Gaussian noise | sigma 0 - 35 (0-255 scale) | 0.3 |
| JPEG re-compression | quality 15 - 95 | 0.25 |

Motion blur, speckle and salt-and-pepper noise never occur in training; they measure robustness to
unseen defect types. The evaluation degradations are a separate numpy/OpenCV implementation, so no
model is tested on the exact code it was trained with.

### 4.4 Evaluation

**Clean test set**: accuracy, top-3/top-5 accuracy, macro and weighted precision / recall / F1,
balanced accuracy, Cohen's kappa, MCC, macro one-vs-rest ROC-AUC and PR-AUC, log loss, Brier score,
expected calibration error (ECE, 15 bins), the accuracy / coverage curve of a confidence threshold
(the app answers only above 70% confidence) and its area (AURC). 95% confidence intervals come from
1,000 bootstrap resamples of the test photos; pairs of models are compared with McNemar's test
(continuity-corrected, exact binomial below 25 disagreements).

**Cross-dataset (PlantDoc)**: *open set*, where the model chooses among all 38 classes as in the
app, and *restricted*, where it chooses among the 27 classes PlantDoc contains. Macro averages are
taken over the classes present. Also reported: crop accuracy and healthy-vs-diseased accuracy.

**Robustness**: a fixed stratified subset of the test set (at most 50 photos per class, 1,873
photos) is degraded at 116 levels across 11 degradation types (Table A2); every model receives the
same degraded photos, each degraded with its own seeded random generator. Summary measures: mean
accuracy over degraded levels (seen and unseen types), relative robustness (corrupted / clean
accuracy) and mCE with E1 as 100 [4]. Low light is a 7 x 6 grid of brightness (x0.1 - x1.0) and
noise (sigma 0 - 45).

**Calibration**: temperature scaling [6] fitted on the validation set (minimum log loss); reported
on the PlantVillage and PlantDoc test sets, together with its effect on the 70% threshold.

### 4.5 Image-quality measures and the quality gate

On the 224 x 224 image the model sees: brightness = mean luma (Rec. 601); contrast = standard
deviation of luma; sharpness = variance of the 4-neighbour Laplacian of luma; noise = Immerkaer's
estimator [8] per colour channel, averaged; resolution = shorter side of the original photo;
glare / crushed shadows = share of pixels with luma >= 250 / <= 5. Because noise is measured after
the resize to 224 px, sensor noise that the resize averages away (most noise in a full-resolution
phone photo) does not count against the photo.

For each degradation type, the tolerated limit is where accuracy falls more than 5 percentage
points below clean accuracy (linear interpolation between levels). The sweep also recorded the
median measured quality of the degraded photos at every level, so each limit is converted into the
measurable units above. These are the paper's minimum image-quality requirements and the
thresholds of the app's quality gate, which returns retake advice (in Hindi and English) for each
problem it finds.

**Automatic correction** (ablation): photos the gate flags as too dark, too bright, flat or grainy
are corrected before classification (median filter, then an exposure gain towards the median
training brightness, then a percentile contrast stretch); good photos pass unchanged.

### 4.6 Deployment

Models are rebuilt in float32 on the TensorFlow backend and converted to TFLite in float32,
float16, dynamic-range int8 and full int8 (calibrated on 190 training photos). Reported: file size,
single-photo latency on the CPU (4 threads, XNNPACK) and accuracy on a 50-per-class test subset.

## 5. Results

Full tables: `research/results/paper/table_*.tex` (LaTeX) and `RESULTS.md`; figures: `fig_*.pdf`.

### 5.1 Clean PlantVillage test set

| Model | Accuracy % (95% CI) | Macro-F1 % (95% CI) | MCC |
| --- | --- | --- | --- |
| E1 MobileNetV2, frozen (original app) | 92.66 (92.07-93.25) | 90.81 (89.97-91.62) | 0.9232 |
| E2 MobileNetV2, fine-tuned | 99.28 (99.09-99.44) | 99.01 (98.70-99.26) | 0.9924 |
| E3 MobileNetV2, fine-tuned + QAA | 98.64 (98.38-98.88) | 98.55 (98.22-98.83) | 0.9857 |
| E4 EfficientNetV2-B0 + QAA | **99.57 (99.43-99.71)** | **99.48 (99.30-99.66)** | 0.9955 |
| E5 MobileNetV3-L + QAA | 99.40 (99.21-99.56) | 99.27 (98.99-99.48) | 0.9937 |
| E6 ResNet50V2 + QAA | 98.38 (98.08-98.66) | 98.08 (97.67-98.46) | 0.9830 |
| E7 DenseNet121 + QAA | 98.78 (98.54-99.03) | 98.62 (98.26-98.93) | 0.9873 |
| E8 EfficientNetV2-B0 + QAA + PlantDoc | 99.50 (99.34-99.64) | 99.48 (99.28-99.65) | 0.9947 |
| C1 handcrafted + Random Forest | 93.89 (93.36-94.38) | 92.34 (91.40-93.08) | 0.9359 |
| C2 handcrafted + SVM | 94.21 (93.70-94.68) | 93.00 (92.23-93.60) | 0.9393 |

Fine-tuning the whole backbone instead of only a new head raises accuracy from 92.66% to 99.28%
(E1 vs E2, McNemar p < 10^-100). QAA costs 0.64 points on clean lab photos (E2 vs E3,
p = 2.6 x 10^-7). EfficientNetV2-B0 is the most accurate backbone (99.57%); MobileNetV3-L is not
significantly different from it (p = 0.055). The two large reference backbones, trained for fewer
epochs at batch size 8, are less accurate than EfficientNetV2-B0 (DenseNet121: p = 1.3 x 10^-10).
Adding PlantDoc photos to training does not cost lab accuracy (E4 vs E8, p = 0.34). Handcrafted
features reach 93.9-94.2%, above the frozen-backbone CNN: on PlantVillage, colour and texture
statistics alone are highly predictive, consistent with the capture bias reported in [3].

### 5.2 Cross-dataset: PlantDoc field photos

| Model | Accuracy % (official / dedup.) | Macro-F1 % | Crop correct % | Healthy vs diseased % |
| --- | --- | --- | --- | --- |
| E1 frozen | 26.81 / 26.70 | 24.68 | 50.64 | 77.02 |
| E2 fine-tuned | 30.21 / 30.32 | 27.11 | 52.77 | 83.83 |
| E3 + QAA | 37.87 / 38.01 | 37.00 | 59.15 | 90.64 |
| E4 EfficientNetV2-B0 + QAA | 34.89 / 36.20 | 34.11 | 62.55 | 86.38 |
| E5 MobileNetV3-L + QAA | 32.77 / 33.03 | 32.08 | 59.15 | 88.94 |
| E6 ResNet50V2 + QAA | 28.51 / 28.96 | 27.27 | 54.47 | 83.40 |
| E7 DenseNet121 + QAA | 27.66 / 28.51 | 26.18 | 51.91 | 87.66 |
| **E8 + PlantDoc training photos** | **63.83 / 65.61** | **62.79** | **85.96** | **94.47** |
| C1 Random Forest | 4.68 / 4.52 | 2.87 | 23.40 | 59.15 |
| C2 SVM | 3.40 / 2.71 | 3.47 | 21.28 | 68.51 |

Every model trained only on PlantVillage loses 61-71 points on field photos (chance: 3.7% with 27
classes). The classical models fall to chance level, although they beat the frozen CNN on
PlantVillage. QAA is the only PlantVillage-only change that significantly improves field accuracy
(E2 vs E3: +7.7 points accuracy, +9.9 points macro-F1, p = 0.007). Larger backbones do not help:
ResNet50V2 and DenseNet121 are significantly worse on field photos than the light models with the
same recipe (E3 vs E6 p = 4.7 x 10^-4; E4 vs E7 p = 0.004). Adding PlantDoc training photos (15% of
each batch) nearly doubles field accuracy, from 34.89% to 63.83% (95% CI 57.9-70.2; p = 2.7 x
10^-13), and the result holds on the deduplicated test set (65.61%), so it is not an effect of
train/test duplicates. For context, Singh et al. [2] report 15.08% (trained on PlantVillage) and
29.73% (fine-tuned on PlantDoc) for VGG16 on uncropped PlantDoc photos at 100 x 100 px, with their
own 80/20 split.

### 5.3 Confidence and calibration

Label smoothing leaves every CNN slightly underconfident on PlantVillage (ECE 0.09-0.10).
Temperature scaling fitted on the validation set (T = 0.50-0.58) reduces lab ECE to 0.002-0.013.
On PlantDoc it does the opposite: ECE rises for every model (E8: 0.136 -> 0.260; E4: 0.265 ->
0.508) because the models are overconfident on field photos, and the underconfidence was acting as
a safety margin. At the app's 70% threshold, calibrated E8 would answer 83% of field photos
instead of 65%, but be right on only 68% of the answered ones instead of 74%. The classical SVM is
the extreme case: it answers 44% of PlantDoc photos with more than 70% confidence and is right on
1% of them. Calibration fitted on lab data should therefore not be trusted in the field; the app
keeps the uncalibrated scores.

### 5.4 Brightness

Accuracy (%) on the 1,873-photo robustness subset as exposure changes:

| Brightness | E1 frozen | E2 fine-tuned | E3 + QAA | E4 + QAA | E8 + PlantDoc | E1 + auto-correction | RF | SVM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| x0.10 | 19.9 | 4.2 | 95.2 | 98.7 | 97.9 | 90.0 | 8.0 | 4.2 |
| x0.20 | 46.4 | 29.9 | 97.3 | 99.0 | 98.8 | 90.4 | 21.7 | 4.4 |
| x0.30 | 64.7 | 54.0 | 98.0 | 99.1 | 99.1 | 87.3 | 29.7 | 8.9 |
| x0.50 | 84.3 | 87.8 | 98.6 | 99.3 | 99.4 | 84.2 | 39.1 | 40.8 |
| x1.00 | 92.3 | 98.7 | 98.4 | 99.2 | 99.5 | 92.1 | 91.2 | 93.9 |
| x1.60 | 89.5 | 93.2 | 98.2 | 99.1 | 99.1 | 88.5 | 45.8 | 16.5 |
| x2.00 | 83.2 | 77.3 | 97.6 | 98.7 | 98.9 | 78.7 | 20.0 | 3.8 |
| x3.00 | 49.0 | 41.1 | 88.3 | 93.8 | 93.6 | 39.5 | 8.1 | 2.8 |

Fine-tuning without QAA makes the network *more* sensitive to exposure than the frozen baseline:
at x0.1, E2 keeps 4.2% accuracy and E1 19.9%. With QAA the fine-tuned models stay within 1-4
points of clean accuracy from x0.1 to x2.0, beyond the x0.25-x2.2 range they were trained with
on the dark side. Automatic exposure correction rescues very dark photos for the non-robust model
(E1: 19.9% -> 90.0% at x0.1) but does not help over-exposed ones, whose clipped highlights cannot
be recovered. Handcrafted colour features fail outside about x0.8-x1.2.

### 5.5 Noise

| Gaussian noise sigma | E1 | E2 | E3 + QAA | E4 + QAA | E8 | RF | SVM | measured noise |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 92.3 | 98.7 | 98.4 | 99.2 | 99.5 | 91.2 | 93.9 | 4.1 |
| 10 | 79.8 | 96.1 | 98.3 | 99.4 | 99.3 | 62.2 | 86.8 | 11.1 |
| 20 | 48.3 | 65.6 | 97.7 | 99.3 | 99.1 | 28.8 | 67.4 | 20.4 |
| 30 | 25.4 | 24.6 | 97.4 | 99.0 | 98.8 | 15.7 | 47.2 | 29.8 |
| 50 | 7.1 | 9.0 | 93.9 | 98.2 | 97.5 | 10.7 | 20.1 | 47.5 |
| 80 | 3.4 | 5.8 | 76.8 | 95.0 | 93.5 | 9.5 | 8.0 | 68.6 |

| Unseen noise | E1 | E2 | E3 + QAA | E4 + QAA | E8 |
| --- | --- | --- | --- | --- | --- |
| salt & pepper 2% | 52.0 | 84.4 | 94.3 | 99.2 | 98.3 |
| salt & pepper 10% | 36.6 | 26.3 | 90.2 | 96.4 | 96.2 |
| speckle var 0.05 | 35.2 | 40.3 | 97.1 | 99.1 | 98.8 |
| speckle var 0.2 | 10.0 | 7.7 | 93.0 | 97.9 | 97.3 |

Without QAA, accuracy halves by sigma 20 (E1 48.3%, E2 65.6%). With QAA it stays above 97% up to
sigma 30 (trained up to 35) and above 93% at sigma 80 for EfficientNetV2-B0. The gain transfers to
the two noise types never seen in training: at 10% salt-and-pepper pixels E4 keeps 96.4% (E2
26.3%), at speckle variance 0.2 it keeps 97.9% (E2 7.7%). The noise estimate of the quality gate
tracks the added noise closely (sigma 30 -> 29.8).

### 5.6 Blur, compression, resolution and contrast

| Degradation | E1 | E2 | E3 + QAA | E4 + QAA | E5 + QAA | E8 | RF | SVM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gaussian blur sigma 2 px | 68.2 | 64.4 | 98.3 | 99.4 | 99.4 | 99.4 | 24.7 | 11.3 |
| Gaussian blur sigma 5 px | 19.3 | 7.7 | 82.7 | 92.1 | 93.4 | 90.6 | 19.5 | 2.7 |
| motion blur 9 px (unseen) | 45.7 | 63.9 | 96.2 | 99.2 | 99.3 | 99.1 | - | - |
| motion blur 17 px (unseen) | 22.5 | 25.1 | 80.8 | 96.1 | 95.2 | 92.5 | - | - |
| JPEG quality 20 | 76.4 | 91.8 | 97.0 | 98.7 | 98.9 | 98.9 | 70.5 | 66.8 |
| JPEG quality 10 | 38.0 | 53.1 | 93.6 | 97.0 | 95.9 | 96.1 | 30.4 | 24.2 |
| resolution 48 px | 56.5 | 53.1 | 97.5 | 99.0 | 99.0 | 98.9 | 24.3 | 9.0 |
| resolution 32 px | 30.9 | 26.7 | 91.7 | 97.5 | 96.0 | 96.0 | 22.4 | 3.6 |
| contrast x0.2 | 49.0 | 9.1 | 95.9 | 99.0 | 97.6 | 98.3 | 21.5 | 19.0 |
| contrast x3.0 | 74.1 | 70.9 | 97.2 | 98.6 | 98.4 | 98.6 | 15.6 | 6.2 |

Blur and low resolution hurt the non-robust models most: two pixels of Gaussian blur cost E1 and
E2 about a third of their accuracy, while the QAA models lose under one point. Motion blur, never
used in training, is the hardest defect for every model, but the QAA models still keep 92-96% at a
17-pixel streak. JPEG compression matters only below quality ~20 for the robust models. As with
brightness, fine-tuning without QAA is often *more* fragile than the frozen baseline (contrast
x0.2: E2 9.1% vs E1 49.0%).

### 5.7 Automatic photo correction

The correction helps the non-robust baseline exactly where it triggers: very dark photos (x0.1:
19.9% -> 90.0%), flat photos (contrast x0.2: 49.0% -> 89.9%) and impulse noise (5% salt-and-pepper:
40.0% -> 86.6%). It does not help blur, compression, colour cast or resolution, which it does not
address, nor over-exposure, whose clipped highlights cannot be restored. Applied to the robust
model it can hurt (speckle variance 0.2: E3 93.0% -> 72.8%), because the median filter removes
texture the model has learned to read through noise. Correction is therefore useful only for a
model trained without QAA; the deployed app leaves it off.

### 5.8 Minimum image quality

Limits where accuracy falls 5 points below clean accuracy, converted to the measured quality of the
degraded photos (median over the robustness subset; brightness and contrast on a 0-255 scale;
sharpness = variance of the Laplacian on the 224 px image; noise = Immerkaer sigma):

| Requirement | E1 frozen (original app) | E2 fine-tuned | E3 + QAA | E8 (deployed) |
| --- | --- | --- | --- | --- |
| Brightness (mean luma) | 70 - 201 | 73 - 188 | >= 12 (whole tested range) - 231 | >= 12 (whole tested range) - 236 |
| Exposure factor | x0.57 - x1.76 | x0.60 - x1.58 | x0.10 - x2.58 | x0.10 - x2.89 |
| Contrast (luma s.d.) | >= 23.8 | >= 26.6 | >= 7.2 | >= 6.0 |
| Noise sigma (strictest of 3 types) | <= 4.6 | <= 7.6 | <= 13.7 | <= 42.6 |
| Sharpness (strictest of 2 blur types) | >= 152 | >= 111 | >= 37 | >= 27 |
| Gaussian blur sigma | <= 1.2 px | <= 1.1 px | <= 4.1 px | <= 4.4 px |
| Motion blur length | <= 3.3 px | <= 4.4 px | <= 11.3 px | <= 15.2 px |
| JPEG quality | >= 41 | >= 24 | >= 10 | >= 10 |
| Leaf resolution | >= 91 px | >= 96 px | >= 37 px | >= 30 px |

For the deployed model, the practical requirements are modest: a leaf at least ~30 px across in
the photo (any phone camera, if the leaf fills a reasonable part of the frame), mean brightness
below ~236 (no blown-out sunlight), visible contrast, sharpness above 27 (a steady hand: motion
blur under ~15 px at 224 px) and JPEG quality 10 or better (ordinary messaging-app compression is
fine). The original frozen model needed a far better photo: brightness 70-201, almost no noise
(sigma <= 4.6), sharp focus (blur <= 1.2 px) and a leaf of 91 px or more. These limits are the
thresholds of the app's quality gate (`models/quality_thresholds.json`).

### 5.9 Low light: dark and noisy together

Accuracy (%) when a photo is darkened and then given sensor noise (rows: brightness factor;
columns: noise sigma):

| | E1 sigma 0 | 10 | 20 | 30 | E8 sigma 0 | 10 | 20 | 30 | 45 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| x0.10 | 19.9 | 4.1 | 2.5 | 2.7 | 97.9 | 84.8 | 49.4 | 27.2 | 10.8 |
| x0.20 | 46.4 | 10.0 | 2.6 | 2.7 | 98.8 | 97.2 | 90.9 | 79.0 | 53.6 |
| x0.30 | 64.7 | 20.1 | 5.2 | 2.8 | 99.1 | 98.8 | 96.4 | 92.0 | 78.9 |
| x0.50 | 84.3 | 42.7 | 15.1 | 5.2 | 99.4 | 99.2 | 98.6 | 96.7 | 93.1 |
| x1.00 | 92.3 | 81.2 | 48.5 | 24.8 | 99.5 | 99.5 | 99.4 | 99.0 | 98.4 |

Darkness and noise compound: each alone costs the deployed model at most two points, together
they are the one condition in which it fails (x0.1 with sigma 20: 49.4%). The baseline is at
chance level from x0.3 with sigma 20. Automatic correction rescues dark photos only when they are
clean (E1 at x0.1, sigma 0: 19.9% -> 89.3%); with noise, raising the exposure raises the noise too
and the correction gains nothing. Real low-light phone photos are therefore the main remaining
failure mode, and the quality gate's "too dark" and "grainy" advice (take the photo in daylight)
targets exactly this case.

### 5.10 Robustness summary

| Model | Clean % | Corrupted %, seen types | Corrupted %, unseen types | Relative robustness % | mCE |
| --- | --- | --- | --- | --- | --- |
| E1 MobileNetV2, frozen | 92.33 | 66.13 | 39.30 | 63.70 | 100.0 |
| E2 MobileNetV2, fine-tuned | 98.66 | 67.30 | 48.51 | 63.02 | 92.7 |
| E3 MobileNetV2 + QAA | 98.44 | 93.53 | 89.42 | 93.87 | 18.9 |
| E4 EfficientNetV2-B0 + QAA | 99.20 | 96.72 | 96.71 | 97.50 | **8.5** |
| E5 MobileNetV3-L + QAA | 99.52 | 96.38 | 95.80 | 96.69 | 9.8 |
| E8 EfficientNetV2-B0 + QAA + PlantDoc | 99.46 | 96.18 | 95.27 | 96.45 | 10.2 |
| E6 ResNet50V2 + QAA * | 98.39 | 92.85 | - | 94.37 | 18.7 |
| E7 DenseNet121 + QAA * | 98.71 | 93.99 | - | 95.22 | 15.6 |
| E1 + automatic correction | 92.06 | 69.42 | 48.24 | 69.13 | 88.0 |
| E3 + automatic correction | 98.39 | 91.90 | 86.30 | 91.85 | 21.7 |
| C1 Random Forest * | 91.20 | 37.19 | - | 40.78 | 171.3 |
| C2 SVM * | 93.88 | 37.88 | - | 40.35 | 172.2 |

\* evaluated on 6 of the 11 degradation types (brightness, contrast, Gaussian noise, Gaussian blur,
JPEG, resolution); their mCE is over those types only.

QAA cuts the corruption error of MobileNetV2 by a factor of five (mCE 92.7 -> 18.9), and the
efficient modern backbones cut it to about a tenth of the baseline (8.5-10.2). Fine-tuning alone
barely changes robustness (100 -> 92.7) although it adds 6.3 points of clean accuracy, so clean
accuracy is a poor predictor of robustness. QAA models lose only 1-4 points between seen and unseen
defect types, so they generalise beyond the defects they were trained with. Handcrafted features
are the least robust by a wide margin (mCE ~172).

### 5.11 Deployment

| Model | Parameters | GFLOPs | Keras CPU ms | TFLite fp16: MB / ms | TFLite int8: MB / ms / accuracy % |
| --- | --- | --- | --- | --- | --- |
| E1 / E2 / E3 MobileNetV2 | 2.31 M | 0.61 | 113-121 | 4.35 / 2.0 | 2.63 / 2.1-2.2 / 91.09 (E1), 98.44 (E3) |
| E5 MobileNetV3-L | 3.03 M | 0.44 | 141 | - | - |
| E4 / E8 EfficientNetV2-B0 | 5.97 M | 1.46 | 243 | 11.33 / 5.8 | 6.85 / 4.8 / 99.30 (E8) |
| E6 ResNet50V2 | 23.64 M | 6.99 | 204 | - | - |
| E7 DenseNet121 | 7.08 M | 5.70 | 380 | - | - |

(GFLOPs count multiplications and additions separately for one 224 x 224 photo.)

TFLite runs every mobile model in 2-6 ms per photo on a laptop CPU (4 threads), 40-60 times faster
than Keras eager inference. Float16 halves the file with no accuracy change; full-integer
quantization costs 0.16 points for the deployed E8 (99.46% -> 99.30% on the 1,900-photo subset,
99.73% agreement with float32) but 1.2 points for the frozen E1, whose features are less
separable. Dynamic-range int8 is the slowest variant on XNNPACK and should not be used. The
deployed model (E8) fits in 6.9 MB as int8.

## 6. Discussion

**Lab accuracy says little about field accuracy.** Every PlantVillage-only model scored 92-99.6% in
the lab and 27-38% in the field, and the ranking changed between the two: the most accurate lab
models (EfficientNetV2-B0, MobileNetV3-L, the large backbones) were not the best in the field, and
handcrafted features beat a frozen CNN in the lab and fell to chance in the field. Results on
PlantVillage alone should not be used to choose a model for deployment.

**Photo defects are a solvable part of the problem.** Without QAA, dark, grainy, blurred or small
photos destroy accuracy, and full fine-tuning makes this worse by fitting PlantVillage's uniform
capture conditions more tightly. QAA removes most of the problem (mCE 92.7 -> 18.9 on the same
backbone, 8.5 with EfficientNetV2-B0) for 0.6 points of lab accuracy, and generalises to defects
it never saw. It also improved field accuracy by 7.7 points, the only PlantVillage-only change
that did so significantly.

**But the lab-to-field gap is not mainly about image quality.** The measured quality of PlantDoc
photos is not worse than PlantVillage's (Figure `fig_quality_lab_vs_field`): they are somewhat
brighter, higher in contrast, similar in sharpness and less noisy. What differs is the scene:
several leaves, soil, hands, sky and clutter instead of one leaf on a plain board. Only training
on field photos closed much of that gap (34.9% -> 63.8%). A practical system therefore needs both:
QAA for the photo defects that farmers' phones produce, and field data for the scene.

**Confidence needs care under domain shift.** Temperature scaling on lab data is the textbook fix
for miscalibration, but here it made field predictions more overconfident. The 70% "not sure"
threshold works best with the uncalibrated scores; calibration for deployment should be fitted on
field data.

**Minimum image quality is a property of the model, not a constant.** The original app's model
needed brightness 70-201, noise below 4.6 and a 91-px leaf; the deployed model accepts brightness
12-236, noise up to 43 and a 30-px leaf. Image-quality guidance given to farmers should be derived
from the deployed model, as done here, and re-derived whenever the model changes.

**Bigger is not better here.** ResNet50V2 (23.6 M parameters, 7.0 GFLOPs) and DenseNet121 were
less accurate in the lab, less robust and worse in the field than EfficientNetV2-B0 (6.0 M, 1.5
GFLOPs) and MobileNetV3-L (3.0 M, 0.4 GFLOPs). The caveat is their shorter, smaller-batch
fine-tuning, forced by 4 GB of GPU memory.

## 7. Limitations

- **Small field test set.** PlantDoc's test set has 235 photos (221 after deduplication), so field
  accuracies carry wide intervals (E8: 57.9-70.2%), and some classes have fewer than ten photos.
  PlantDoc itself contains label noise and web photos, not photos from Indian farms.
- **Synthetic degradations.** The robustness study degrades lab photos; real low light,
  motion and compression combine in ways a single degradation does not capture. The low-light grid
  is one step towards that.
- **One training run per configuration.** Seeds are fixed but no run was repeated, so differences
  between close models (e.g. E4 vs E5) rest on McNemar's test of one run each, not on training
  variance.
- **Unequal budgets for the large backbones.** ResNet50V2 and DenseNet121 were fine-tuned for 4
  epochs at batch size 8 because of GPU memory; with more epochs they may close some of the gap.
- **E8 sees PlantDoc's training photos.** Its field score is an in-distribution result for PlantDoc's
  sources (web images of the same 27 classes), not a guarantee for other regions or crops.
- **Quality thresholds are dataset-calibrated.** Sharpness and noise limits were measured on
  PlantVillage leaves on plain backgrounds; cluttered field scenes change these statistics.
- **Closed set.** The models only know 38 classes; photos of other crops or diseases still receive
  one of them, and the confidence threshold catches only part of these.

## 8. Conclusion

A leaf-disease classifier that scores 99% on PlantVillage can fail on a farmer's photo for two
separate reasons: photo defects and scene differences. Quality-aware augmentation makes lightweight
CNNs robust to the first (corruption error cut to 8.5-19% of the baseline, little loss of lab
accuracy, generalisation to unseen defects) and adding field photos addresses the second (field
accuracy 34.9% -> 63.8% with EfficientNetV2-B0, 99.5% retained in the lab). Measured against the
deployed model, the minimum photo a farmer needs is modest: the leaf at least ~30 px across, not
in blown-out sunlight (mean brightness <= 236), visible contrast, held steady (motion blur under
~15 px at 224 px) and saved at JPEG quality 10 or better; the main failure that remains is a photo
that is both dark and grainy. The model runs in 5 ms per photo and 7 MB as int8 TFLite. Lab
accuracy alone is not a sufficient criterion for choosing a model for the field.

## Appendix

### Table A1. PlantDoc folders and the PlantVillage class each maps to

| PlantDoc folder | PlantVillage class |
| --- | --- |
| apple scab leaf | Apple - Apple scab |
| apple leaf | Apple - healthy |
| apple rust leaf | Apple - Cedar apple rust |
| bell pepper leaf | Pepper, bell - healthy |
| bell pepper leaf spot | Pepper, bell - Bacterial spot |
| blueberry leaf | Blueberry - healthy |
| cherry leaf | Cherry (including sour) - healthy |
| corn gray leaf spot | Corn (maize) - Cercospora leaf spot Gray leaf spot |
| corn leaf blight | Corn (maize) - Northern Leaf Blight |
| corn rust leaf | Corn (maize) - Common rust  |
| peach leaf | Peach - healthy |
| potato leaf | Potato - healthy |
| potato leaf early blight | Potato - Early blight |
| potato leaf late blight | Potato - Late blight |
| raspberry leaf | Raspberry - healthy |
| soyabean leaf | Soybean - healthy |
| squash powdery mildew leaf | Squash - Powdery mildew |
| strawberry leaf | Strawberry - healthy |
| tomato early blight leaf | Tomato - Early blight |
| tomato septoria leaf spot | Tomato - Septoria leaf spot |
| tomato leaf | Tomato - healthy |
| tomato leaf bacterial spot | Tomato - Bacterial spot |
| tomato leaf late blight | Tomato - Late blight |
| tomato leaf mosaic virus | Tomato - Tomato mosaic virus |
| tomato leaf yellow virus | Tomato - Tomato Yellow Leaf Curl Virus |
| tomato mold leaf | Tomato - Leaf Mold |
| tomato two spotted spider mites leaf | Tomato - Spider mites Two-spotted spider mite |
| grape leaf | Grape - healthy |
| grape leaf black rot | Grape - Black rot |

### Table A2. Degradation types and levels of the robustness study

| Type | Levels | In QAA training? |
| --- | --- | --- |
| Brightness factor | 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3 | yes |
| Contrast factor | 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1, 1.3, 1.6, 2, 2.5, 3 | yes |
| Gamma | 0.3, 0.5, 0.7, 1, 1.5, 2, 2.5, 3, 4 | yes |
| Colour cast (cool <- 0 -> warm) | -0.5, -0.4, -0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5 | yes |
| Gaussian noise sigma | 0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80 | yes |
| Salt & pepper amount | 0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.15, 0.2 | no (unseen) |
| Speckle variance | 0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5 | no (unseen) |
| Gaussian blur sigma (px) | 0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7 | yes |
| Motion blur length (px) | 1, 3, 5, 7, 9, 13, 17, 21, 29 | no (unseen) |
| JPEG quality | 100, 90, 75, 50, 30, 20, 15, 10, 5, 2 | yes |
| Effective resolution (px) | 224, 192, 160, 128, 96, 80, 64, 48, 32, 24, 16 | yes |

116 levels in total, including each type's clean level. Low-light grid: brightness 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1 x noise sigma 0, 5, 10, 20, 30, 45.

## References

1. S. P. Mohanty, D. P. Hughes, M. Salathé. Using deep learning for image-based plant disease
   detection. *Frontiers in Plant Science* 7:1419, 2016. arXiv:1604.03169.
2. D. Singh, N. Jain, P. Jain, P. Kayal, S. Kumawat, N. Batra. PlantDoc: A dataset for visual plant
   disease detection. *Proc. CoDS-COMAD*, 2020. arXiv:1911.10317.
3. M. A. Noyan. Uncovering bias in the PlantVillage dataset. arXiv:2206.04374, 2022.
4. D. Hendrycks, T. Dietterich. Benchmarking neural network robustness to common corruptions and
   perturbations. *ICLR*, 2019.
5. S. Dodge, L. Karam. Understanding how image quality affects deep neural networks. *QoMEX*, 2016.
6. C. Guo, G. Pleiss, Y. Sun, K. Q. Weinberger. On calibration of modern neural networks. *ICML*,
   2017.
7. D. P. Hughes, M. Salathé. An open access repository of images on plant health to enable the
   development of mobile disease diagnostics. arXiv:1511.08060, 2015.
8. J. Immerkær. Fast noise variance estimation. *Computer Vision and Image Understanding* 64(2),
   300-302, 1996.

*Check references 4, 5, 6 and 8 against the publishers' pages before submission; 1-3 were checked
against the papers on 2026-11-25.*
