# Kisan Sahayak: An AI-Powered Smart Farming Assistant

A minor project for Indian farmers with three AI modules: crop disease
detection (built), crop recommendation and a Hindi/English farmer chatbot
(both in progress). This README currently covers Module 1.

## Module 1: Crop disease detection

A farmer uploads (or takes) a photo of a leaf. The app names the crop and the
disease, shows how confident it is, and lists the cause, symptoms, treatment
and prevention.

The model is a convolutional neural network (MobileNetV2) trained with
transfer learning on the [PlantVillage](https://github.com/spMohanty/PlantVillage-Dataset)
dataset: 38 classes covering 14 crops (apple, cherry, maize, grape, orange,
peach, bell pepper, potato, squash, strawberry, tomato and more), 26 diseases
plus healthy leaves.

## How it works

```
leaf photo ──> resize to 224x224 ──> MobileNetV2 (pre-trained on ImageNet)
           ──> global average pooling ──> dropout ──> dense softmax (38 classes)
           ──> disease name + confidence ──> treatment advice (disease_info.json)
```

1. **Transfer learning.** MobileNetV2 already knows how to see edges, textures
   and shapes from 1.2 million ImageNet photos. We keep those layers frozen
   and train only a new final layer for our 38 leaf classes.
2. **Fine-tuning (optional).** The last 30 MobileNetV2 layers are unfrozen and
   trained with a very small learning rate so they adapt to leaves.
3. **Data augmentation.** Random flips, rotation, zoom and contrast changes
   during training, so the model copes with photos taken at different angles
   and in different light.
4. **Class weights.** Some classes have ten times more photos than others;
   weighting the loss stops the model ignoring the rare ones.
5. **Honest evaluation.** The photos are split 70% train / 15% validation /
   15% test. The test photos are never seen during training.

## Project layout

| Path | What it is |
| --- | --- |
| `app.py` | Streamlit web app |
| `kisan/disease/train.py` | Training and evaluation script |
| `kisan/disease/predict.py` | Loads the model and classifies a photo |
| `kisan/disease/labels.py` | Readable crop and disease names, treatment lookup |
| `kisan/disease/disease_info.json` | Cause, symptoms, treatment and prevention for each disease |
| `notebooks/01_disease_model_colab.ipynb` | The same training as a Google Colab notebook (full dataset, GPU, fine-tuning) |
| `scripts/download_data.py` | Downloads the PlantVillage images |
| `models/` | Trained model (`plant_disease.keras`) and class list |
| `reports/` | Accuracy, classification report, training curves, confusion matrix |
| `tests/` | Unit tests |

## Setup

Needs Python 3.10 to 3.12 and git.

```bash
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501, upload a leaf photo and read the result. A trained
model is already in `models/`, so this works straight after cloning.

## Train the model yourself

```bash
python scripts/download_data.py              # a quarter of the dataset (~13,500 photos)
python scripts/download_data.py --parts 16   # or the full dataset (~54,000 photos)

python -m kisan.disease.train                      # train the top layer (fine on a laptop CPU)
python -m kisan.disease.train --fine-tune-epochs 5 # plus fine-tuning (use a GPU, e.g. Google Colab)
```

Training writes the model to `models/` and these files to `reports/`:

- `metrics.json`: test accuracy and the accuracy/loss of every epoch
- `classification_report.txt`: precision, recall and F1-score per class
- `training_curves.png`: accuracy and loss over the epochs
- `confusion_matrix.png`: which classes get confused with which

## Run the tests

```bash
python -m pytest
```

## Results

See `reports/metrics.json` and `reports/classification_report.txt` for the
numbers of the model in `models/`.

## Limitations

- PlantVillage photos were taken in a lab: one leaf on a plain background.
  Accuracy on photos taken in a field, with several leaves, soil and shadows,
  is lower than the test accuracy.
- The model only knows the 38 classes it was trained on. A photo of any other
  crop or disease still gets one of those 38 answers; the app warns when the
  confidence is below 70% and advises consulting the local KVK.
- The treatment advice is general. Doses, approved products and safety periods
  differ by region, so farmers should confirm with the local agriculture
  officer or Krishi Vigyan Kendra.

## Possible extensions

- Hindi and regional-language interface
- Field-condition photos added to the training data (e.g. the PlantDoc dataset)
- Grad-CAM heatmap showing which part of the leaf the model looked at
- A crop recommendation module from soil N-P-K, pH, rainfall and temperature
- A TensorFlow Lite version of the model for an offline Android app
