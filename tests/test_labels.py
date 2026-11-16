import json

import numpy as np
from PIL import Image

from kisan.disease.labels import INFO_PATH, disease_info, parse_label
from kisan.disease.predict import prepare_image


def test_parses_simple_class():
    label = parse_label("Tomato___Late_blight")
    assert (label.crop, label.condition, label.healthy) == ("Tomato", "Late blight", False)


def test_parses_awkward_names():
    assert parse_label("Corn_(maize)___Common_rust_").title == "Corn (maize) - Common rust"
    assert parse_label("Pepper,_bell___Bacterial_spot").crop == "Pepper, bell"
    assert parse_label("Tomato___Spider_mites Two-spotted_spider_mite").condition == (
        "Spider mites Two-spotted spider mite")


def test_healthy_class():
    label = parse_label("Apple___healthy")
    assert label.healthy and label.condition == "Healthy"


def test_info_lookup_ignores_punctuation_differences():
    assert disease_info("Corn_(maize)___Common_rust") == disease_info("Corn_(maize)___Common_rust_")
    assert disease_info("Apple___healthy") is None


def test_every_disease_entry_is_complete():
    entries = json.loads(INFO_PATH.read_text(encoding="utf-8"))
    assert len(entries) == 26  # PlantVillage: 38 classes, 12 of them healthy
    for name, entry in entries.items():
        assert not parse_label(name).healthy
        assert entry["cause"] and entry["symptoms"], name
        assert entry["treatment"] and entry["prevention"], name


def test_prepare_image_keeps_0_255_range():
    image = Image.new("RGBA", (640, 480), (255, 0, 0, 255))
    batch = prepare_image(image, 224)
    assert batch.shape == (1, 224, 224, 3)
    assert batch.dtype == np.float32
    assert batch.max() == 255.0 and batch[0, 0, 0].tolist() == [255.0, 0.0, 0.0]
