# Kisan Sahayak: An AI-Powered Smart Farming Assistant

A web product for Indian farmers. Photograph one leaf and Kisan Sahayak names
the disease, shows how confident it is, and gives organic and chemical
treatment options, in Hindi or English.

| Module | What it does |
| --- | --- |
| 1. Disease scan | A CNN names the disease on a leaf photo and gives organic and chemical treatment |
| 2. Crop advisor | A Random Forest recommends a crop from soil N-P-K, pH, temperature, humidity and rainfall, and shows why |
| 3. Farming assistant | Answers questions in Hindi or English from a set of agriculture documents (RAG with Claude) |

Built for farmers who are not comfortable with reading and typing:

- **Voice.** Results and answers can be read aloud, and questions can be spoken.
- **Spraying weather.** One tap shows whether today is dry and calm enough to spray.
- **No soil test needed.** Low / Medium / High presets, and temperature and humidity filled from the local weather.
- **Honest about doubt.** Below 70% confidence every module says so and points to the Krishi Vigyan Kendra.
- **Helpline.** The Kisan Call Centre number (1800-180-1551) is one tap away.
- **Explains its results.** The assistant knows the latest scan or crop result, so "what should I do about this?" needs no retyping.

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

python -m kisan.chatbot.ingest   # once: downloads the embedding model (~220 MB), indexes the documents
python -m api.server             # serves the website and the API
```

Open http://localhost:8000. The trained models are already in `models/`.

### The assistant's API key

The assistant writes full answers with Claude, which needs an API key:

1. Copy `.env.example` to `.env`.
2. Put your key after `ANTHROPIC_API_KEY=` (create one at https://console.anthropic.com/).
3. Restart the server.

Without a key the assistant runs in basic mode: it finds the matching passages
and shows them as they are. The key is read from `.env`, which is never committed.

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
| `GET /api/crop/meta` | Crops, input ranges and presets, the real model comparison |
| `POST /api/crop/recommend` | JSON with the seven values: top crops, confidence, reasons |
| `GET /api/chat/status` | Whether an API key is set and how many documents are indexed |
| `POST /api/chat` | JSON with `message`, `language`, `history`, `context`: answer and sources |

Errors come back as `{"error": {"code": "...", "message": "..."}}`. Codes:
`no_file`, `invalid_image`, `image_too_small`, `file_too_large`, `invalid_input`
(with the `field`), `empty_message`, `model_missing`, `index_missing`.

## How the crop advisor works

`python -m kisan.crop.train` compares four models with 5-fold cross-validation
on the Crop Recommendation dataset (2,200 rows, 22 crops), keeps the best one
and tests it once on a held-out 20%. The comparison, confusion matrix, feature
importance and EDA plots are written to `reports/crop/`.

To explain a recommendation, the app compares each value the farmer entered
with the range that crop grows in (5th to 95th percentile in the data). A
recommendation is marked uncertain when confidence is below 70% or a value is
outside anything the model was trained on.

Download the data with `python scripts/download_crop_data.py`.

## How the assistant works (RAG)

```
question ──> embed ──> FAISS: nearest passages ──> Claude: answer only from these ──> answer + sources
                        (knowledge_base/*.md)        (plus the farmer's latest result)
```

1. **Chunk.** Each document in `knowledge_base/` is split into one passage per section.
2. **Embed.** A multilingual sentence-embedding model turns each passage into a
   vector, so a Hindi question lands near the English passage that answers it.
3. **Retrieve.** FAISS returns the passages closest to the question; weak
   matches are dropped.
4. **Generate.** Claude receives the passages, the farmer's latest scan or crop
   result and the question, with instructions to answer only from the passages
   and to say so when they do not contain the answer.

Replace the files in `knowledge_base/` with your own documents and run
`python -m kisan.chatbot.ingest` again. The starter documents are general
guidance written for this project; check them against the official sources
named at the top of each file.

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
| `web/src/pages/app/` | Dashboard: layout, overview, disease scan, crop advisor, assistant |
| `web/src/lib/speech.js`, `weather.js` | Read-aloud and voice typing; local weather from Open-Meteo |
| `kisan/crop/` | Crop model: training with model comparison, prediction with reasons |
| `kisan/chatbot/` | Assistant: `ingest.py` (index), `retriever.py` (search), `chat.py` (Claude) |
| `knowledge_base/` | The documents the assistant answers from |
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
- The Crop Recommendation dataset is small and very clean, which is why every
  model scores near 99%. Real fields are messier, and the model knows nothing
  about season, water supply, market prices or seed availability.
- The Low / Medium / High presets are percentiles of the training data, not the
  official Soil Health Card ratings.
- The assistant is only as good as the documents in `knowledge_base/`.
- Voice typing depends on the browser (Chrome, Edge and Android browsers
  support it); the weather features need internet and location permission.
- The treatment advice is general and in English. Doses, approved products and
  waiting periods differ by region, so farmers should confirm with the local
  agriculture officer or Krishi Vigyan Kendra.
