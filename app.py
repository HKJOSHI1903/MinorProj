"""Kisan Sahayak web app (Module 1 only for now): upload a leaf photo, get the disease and what to do about it.

    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError

from kisan.disease.labels import disease_info, parse_label
from kisan.disease.predict import LOW_CONFIDENCE, ModelNotTrained, load_model, predict

ROOT = Path(__file__).parent
METRICS_PATH = ROOT / "reports" / "metrics.json"

st.set_page_config(page_title="Kisan Sahayak - Crop Disease Detection", page_icon="🌿", layout="centered")


@st.cache_resource(show_spinner="Loading the model...")
def get_model():
    return load_model()


def sidebar(class_names: list[str]) -> None:
    with st.sidebar:
        st.header("About")
        st.write(
            "Kisan Sahayak looks at a photo of a single leaf and names the disease. "
            "It uses a MobileNetV2 neural network trained on the PlantVillage dataset."
        )
        if METRICS_PATH.exists():
            metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            st.metric("Accuracy on unseen test photos", f"{metrics['test_accuracy']:.1%}")
            st.caption(f"Trained on {metrics['images']['train']:,} photos, "
                       f"tested on {metrics['images']['test']:,}.")

        st.header("Supported crops")
        crops: dict[str, list[str]] = {}
        for name in class_names:
            label = parse_label(name)
            crops.setdefault(label.crop, [])
            if not label.healthy:
                crops[label.crop].append(label.condition)
        for crop, diseases in crops.items():
            with st.expander(crop):
                if diseases:
                    for disease in diseases:
                        st.write(f"- {disease}")
                else:
                    st.write("Healthy leaves only (no disease classes in the dataset).")


def show_result(image: Image.Image) -> None:
    with st.spinner("Checking the leaf..."):
        results = predict(image, top_k=3)
    best = results[0]

    left, right = st.columns([1, 1])
    with left:
        st.image(image, caption="Your photo", use_container_width=True)
    with right:
        st.caption("Crop")
        st.subheader(best.label.crop)
        st.caption("Result")
        if best.label.healthy:
            st.success("Healthy leaf")
        else:
            st.error(best.label.condition)
        st.caption("Confidence")
        st.progress(best.confidence, text=f"{best.confidence:.0%}")

    if best.confidence < LOW_CONFIDENCE:
        st.warning(
            f"The model is not sure about this photo (confidence below {LOW_CONFIDENCE:.0%}). "
            "Do not rely on this result. Take a close photo of one leaf on a plain background "
            "in good light and try again, and consult your local Krishi Vigyan Kendra (KVK) or "
            "agriculture officer before treating the crop."
        )

    if best.label.healthy:
        st.info("No disease found. Keep checking the crop regularly, water at the base of the "
                "plant and remove weeds and fallen leaves.")
    else:
        info = disease_info(best.label.class_name)
        if info:
            st.markdown("#### Cause")
            st.write(info["cause"])
            st.markdown("#### Symptoms")
            st.write(info["symptoms"])
            st.markdown("#### Treatment")
            for step in info["treatment"]:
                st.write(f"- {step}")
            st.markdown("#### Prevention")
            for step in info["prevention"]:
                st.write(f"- {step}")
        else:
            st.info("No treatment advice is stored for this disease yet.")

    with st.expander("Other possibilities"):
        for result in results:
            st.progress(result.confidence, text=f"{result.label.title}: {result.confidence:.1%}")

    st.caption(
        "This is a student project, not professional advice. Always read the pesticide label for "
        "the dose and safety period, and confirm with your local agriculture officer or Krishi "
        "Vigyan Kendra before spraying."
    )


def main() -> None:
    st.title("🌿 Kisan Sahayak")
    st.write("Upload a photo of a crop leaf to find out which disease it has and how to treat it.")

    try:
        _, class_names, _ = get_model()
    except ModelNotTrained:
        st.error("The model has not been trained yet.")
        st.code("python scripts/download_data.py\npython -m kisan.disease.train", language="bash")
        st.stop()

    sidebar(class_names)

    upload_tab, camera_tab = st.tabs(["Upload a photo", "Use the camera"])
    with upload_tab:
        uploaded = st.file_uploader("Leaf photo", type=["jpg", "jpeg", "png", "webp"])
    with camera_tab:
        captured = None
        if st.toggle("Turn on the camera"):
            captured = st.camera_input("Take a photo of the leaf")

    source = captured or uploaded
    if source is None:
        st.info("Tip: photograph one leaf, flat, on a plain background, in daylight.")
        return

    try:
        image = Image.open(source)
        image.load()
    except (UnidentifiedImageError, OSError):
        st.error("That file could not be read as an image. Try a JPG or PNG photo.")
        return

    st.divider()
    show_result(image)


main()
