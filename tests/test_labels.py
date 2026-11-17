import json

import numpy as np
from PIL import Image

from kisan.disease.labels import ADVICE_PATH, advice_disclaimer, parse_label, treatment_advice
from kisan.disease.predict import LOW_CONFIDENCE, prepare_image


def model_classes() -> list[str]:
    path = ADVICE_PATH.parents[1] / "models" / "class_names.json"
    return json.loads(path.read_text(encoding="utf-8"))["class_names"]


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


def test_advice_lookup_ignores_punctuation_differences():
    assert treatment_advice("Corn_(maize)___Common_rust") == treatment_advice("Corn_(maize)___Common_rust_")
    assert treatment_advice("Mango___Anthracnose") is None


def test_healthy_classes_get_care_tips():
    advice = treatment_advice("Apple___healthy")
    assert advice["organic"] and advice["prevention"]
    assert "chemical" not in advice


def test_every_model_class_has_complete_advice():
    """Every class the trained model can output must have advice to show."""
    class_names = model_classes()
    assert len(class_names) == 38
    for name in class_names:
        advice = treatment_advice(name)
        assert advice is not None, name
        if not parse_label(name).healthy:
            for field in ("cause", "symptoms", "organic", "chemical", "prevention"):
                assert advice[field], f"{name}: {field}"


def test_advice_file_has_26_diseases_and_a_disclaimer():
    entries = json.loads(ADVICE_PATH.read_text(encoding="utf-8"))["classes"]
    assert len(entries) == 26  # PlantVillage: 38 classes, 12 of them healthy
    assert "General advice" in advice_disclaimer()


def test_prepare_image_keeps_0_255_range():
    image = Image.new("RGBA", (640, 480), (255, 0, 0, 255))
    batch = prepare_image(image, 224)
    assert batch.shape == (1, 224, 224, 3)
    assert batch.dtype == np.float32
    assert batch.max() == 255.0 and batch[0, 0, 0].tolist() == [255.0, 0.0, 0.0]


def test_low_confidence_threshold_is_70_percent():
    assert LOW_CONFIDENCE == 0.70
