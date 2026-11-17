# Kisan Sahayak: An AI-Powered Smart Farming Assistant

A web product for Indian farmers. Photograph one leaf and Kisan Sahayak names
the disease, shows how confident it is, and gives organic and chemical
treatment options, in Hindi or English.

| Module | Status |
| --- | --- |
| 1. Crop disease detection (CNN on leaf photos) | Built |
| 2. Crop recommendation (soil and weather to best crop) | In development |
| 3. Farmer chatbot (Hindi/English, answers from documents) | In development |

## How it is built

```
Browser (Vue 3)  ──/api──>  Flask server  ──>  MobileNetV2 model (TensorFlow)
 homepage + dashboard        api/server.py      models/plant_disease.keras
```

- **Frontend** (`web/`): Vue 3, Vite, Tailwind CSS, Three.js. A homepage with a
  3D leaf-scan scene and a dashboard (overview, disease scan, upcoming modules).
  Hindi/English toggle, works on phones.
- **Backend** (`api/`): a small Flask API that loads the trained model once and
  answers prediction requests.
- **Model** (`kisan/disease/`): MobileNetV2 with transfer learning on the
  [PlantVillage](https://github.com/spMohanty/PlantVillage-Dataset) dataset,
  38 classes (14 crops, 26 diseases plus healthy leaves).

## Run it

Needs Python 3.10 to 3.12 and Node.js 20 or newer.

```bash
pip install -r requirements.txt

cd web
npm install
npm run build        # builds the website into web/dist
cd ..

python -m api.server # serves the website and the API
```

Open http://localhost:8000. A trained model is already in `models/`.

### While developing the frontend

Run the two parts separately so the page reloads as you edit:

```bash
python -m api.server          # terminal 1: API on port 8000
cd web && npm run dev         # terminal 2: website on http://localhost:5173
```

## API

| Endpoint | What it returns |
| --- | --- |
| `GET /api/health` | Whether the server is up and the model is loaded |
| `GET /api/meta` | Classes, crops, the real training metrics, the 70% threshold |
| `POST /api/disease/predict` | Form field `image`: prediction, confidence, top 3, advice |

Errors come back as `{"error": {"code": "...", "message": "..."}}`. Codes:
`no_file`, `invalid_image`, `image_too_small`, `file_too_large`, `model_missing`.

## How the model works

```
leaf photo ──> resize to 224x224 ──> MobileNetV2 (pre-trained on ImageNet)
           ──> global average pooling ──> dropout ──> dense softmax (38 classes)
           ──> disease name + confidence ──> advice (data/treatment_advice.json)
```

1. **Transfer learning.** MobileNetV2 already knows how to see edges, textures
   and shapes from 1.2 million ImageNet photos. Those layers stay frozen and
   only a new final layer is trained for the 38 leaf classes.
2. **Fine-tuning (optional).** The last 30 MobileNetV2 layers are unfrozen and
   trained with a very small learning rate so they adapt to leaves.
3. **Data augmentation.** Random flips, rotation, zoom and contrast changes
   during training, so the model copes with different angles and light.
4. **Class weights.** Some classes have ten times more photos than others;
   weighting the loss stops the model ignoring the rare ones.
5. **Honest evaluation.** 70% train / 15% validation / 15% test. The test
   photos are never seen during training.
6. **Confidence threshold.** Below 70% the app says the result is uncertain
   and advises consulting the local Krishi Vigyan Kendra.

## Train the model yourself

```bash
python scripts/download_data.py              # a quarter of the dataset (~13,400 photos)
python scripts/download_data.py --parts 16   # or the full dataset (~54,000 photos)

python -m kisan.disease.train                      # train the top layer (fine on a laptop CPU)
python -m kisan.disease.train --fine-tune-epochs 5 # plus fine-tuning (use a GPU)
```

Or open `notebooks/01_disease_model_colab.ipynb` in Google Colab (free GPU):
it trains on the full dataset with fine-tuning and downloads the model.

Training writes the model to `models/` and these files to `reports/`:
`metrics.json`, `classification_report.txt`, `training_curves.png`,
`confusion_matrix.png`. The website reads its accuracy numbers from
`reports/metrics.json`, so it always shows the results of the model in use.

## Project layout

| Path | What it is |
| --- | --- |
| `web/src/pages/Landing.vue` | Homepage |
| `web/src/pages/app/` | Dashboard: layout, overview, disease scan, upcoming modules |
| `web/src/three/LeafScene.js` | The 3D leaf-scan scene (Three.js, custom shader) |
| `web/src/lib/i18n.js` | Hindi and English text |
| `web/src/lib/api.js` | Calls to the Python server |
| `web/src/styles/main.css` | Design tokens and shared styles |
| `api/server.py` | Flask API, also serves the built website |
| `kisan/disease/train.py` | Training and evaluation script |
| `kisan/disease/predict.py` | Loads the model and classifies a photo |
| `kisan/disease/labels.py` | Readable names and treatment lookup |
| `data/treatment_advice.json` | Symptoms, cause, organic and chemical treatment, prevention (general advice) |
| `notebooks/01_disease_model_colab.ipynb` | Colab training notebook |
| `scripts/download_data.py` | Downloads the PlantVillage images |
| `models/`, `reports/` | Trained model and its evaluation results |
| `tests/` | Backend tests (`python -m pytest`) |

## Limitations

- PlantVillage photos were taken in a lab: one leaf on a plain background.
  Accuracy on field photos with several leaves, soil and shadows is lower
  than the test accuracy.
- The model only knows its 38 classes. A photo of anything else still gets one
  of those answers; the 70% threshold catches many of these cases, not all.
- The treatment advice is general and in English. Doses, approved products and
  waiting periods differ by region, so farmers should confirm with the local
  agriculture officer or Krishi Vigyan Kendra.
