"""Tests for the crop recommendation and assistant endpoints.

They use the real crop model and the real search index. Claude is never called:
the tests either run without an API key or replace the call with a stand-in.
"""

import pytest

from api.server import create_app
from kisan.chatbot import chat
from kisan.chatbot.ingest import chunk_document, split_long

RICE = {"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82, "ph": 6.5, "rainfall": 203}


@pytest.fixture(scope="module")
def client():
    return create_app().test_client()


@pytest.fixture
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)


# ---------------- crop recommendation ----------------

def test_crop_meta(client):
    meta = client.get("/api/crop/meta").get_json()
    assert len(meta["crops"]) == 22
    assert set(meta["features"]) == set(RICE)
    presets = meta["features"]["N"]["presets"]
    assert presets["low"] < presets["medium"] < presets["high"]
    assert 0 < meta["metrics"]["test_accuracy"] <= 1
    assert set(meta["metrics"]["cross_validation"]) == {
        "Decision Tree", "Random Forest", "SVM (RBF kernel)", "XGBoost"}


def test_recommends_rice_for_rice_conditions(client):
    body = client.post("/api/crop/recommend", json=RICE).get_json()
    assert body["recommendation"]["crop"] == "rice"
    assert body["low_confidence"] is False
    assert body["alternatives"][0] == body["recommendation"]
    assert all(reason["fits"] for reason in body["reasons"])
    assert [reason["feature"] for reason in body["reasons"]] == list(RICE)


def test_unusual_values_are_flagged_as_low_confidence(client):
    body = client.post("/api/crop/recommend", json={**RICE, "N": 50, "P": 50, "K": 50, "humidity": 60,
                                                    "temperature": 25, "rainfall": 100}).get_json()
    assert body["low_confidence"] is True
    assert body["recommendation"]["confidence"] < 0.70


def test_values_outside_the_training_data_are_flagged(client):
    body = client.post("/api/crop/recommend", json={**RICE, "rainfall": 900}).get_json()
    assert body["outside_training_range"] == ["rainfall"]
    assert body["low_confidence"] is True


@pytest.mark.parametrize("change, field", [
    ({"ph": 15}, "ph"),
    ({"humidity": -5}, "humidity"),
    ({"N": "lots"}, "N"),
    ({"K": None}, "K"),
    ({"temperature": ""}, "temperature"),
])
def test_bad_inputs_are_rejected_with_the_field_name(client, change, field):
    response = client.post("/api/crop/recommend", json={**RICE, **change})
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert (error["code"], error["field"]) == ("invalid_input", field)


def test_missing_body_is_rejected(client):
    assert client.post("/api/crop/recommend", data="hello").status_code == 400


# ---------------- knowledge base ----------------

def test_long_sections_are_split_at_sentence_ends():
    text = " ".join(f"Sentence number {i} is here." for i in range(200))
    pieces = split_long(text)
    assert len(pieces) > 1
    assert all(len(piece) <= 1200 and piece.endswith(".") for piece in pieces)


def test_chunks_keep_document_and_section_titles(tmp_path):
    doc = tmp_path / "sample.md"
    doc.write_text("# Sample doc\n\nIntro line.\n\n## First part\n\n" + "Water the crop in the morning. " * 5
                   + "\n\n## Second part\n\n" + "Remove weeds every week. " * 5, encoding="utf-8")
    chunks = chunk_document(doc)
    assert [(c["title"], c["section"]) for c in chunks] == [("Sample doc", "First part"), ("Sample doc", "Second part")]


# ---------------- assistant ----------------

def test_chat_status_without_key(client, no_api_key):
    status = client.get("/api/chat/status").get_json()
    assert status["ai_available"] is False
    assert status["documents"] >= 8
    assert status["helpline"] == "1800-180-1551"


def test_without_a_key_the_matching_passages_are_returned(client, no_api_key):
    body = client.post("/api/chat", json={"message": "How do I take a soil sample?"}).get_json()
    assert body["mode"] == "passages"
    assert body["passages"][0]["section"] == "How to take a soil sample"
    assert body["sources"][0]["title"] == "Soil health and the Soil Health Card"


def test_hindi_question_finds_the_english_passage(client, no_api_key):
    body = client.post("/api/chat", json={"message": "मिट्टी का नमूना कैसे लें", "language": "hi"}).get_json()
    assert body["passages"][0]["section"] == "How to take a soil sample"


def test_unrelated_question_matches_nothing(client, no_api_key):
    body = client.post("/api/chat", json={"message": "How do I repair a tractor engine?"}).get_json()
    assert body["mode"] == "no_match"
    assert body["sources"] == []


def test_empty_message_is_rejected(client):
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "empty_message"


def test_with_a_key_claude_gets_passages_context_and_language(client, monkeypatch):
    """Claude itself is replaced, so this checks what the app would send it."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    seen = {}

    def fake_ask(message, passages, context, language, history):
        seen.update(turn=chat.build_user_turn(message, passages, context, language), history=history)
        return "उत्तर"

    monkeypatch.setattr(chat, "ask_claude", fake_ask)
    body = client.post("/api/chat", json={
        "message": "इसका इलाज क्या है?",
        "language": "hi",
        "history": [{"role": "user", "content": "नमस्ते"}, {"role": "assistant", "content": "नमस्ते"}, "junk"],
        "context": {"type": "disease", "crop": "Potato", "condition": "Late blight",
                    "confidence": 0.62, "healthy": False, "low_confidence": True},
    }).get_json()

    assert body["mode"] == "ai" and body["answer"] == "उत्तर"
    assert "Late blight of potato and tomato" in seen["turn"]          # retrieved using the scan result
    assert "crop Potato, Late blight, model confidence 62%" in seen["turn"]
    assert "LOW CONFIDENCE" in seen["turn"]
    assert "Reply language: Hindi" in seen["turn"]
    assert len(seen["history"]) == 2                                    # the junk entry was dropped


def test_if_claude_fails_the_passages_are_still_returned(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def failing_ask(*_args):
        raise chat.AssistantUnavailable("The assistant could not be reached.")

    monkeypatch.setattr(chat, "ask_claude", failing_ask)
    body = client.post("/api/chat", json={"message": "When should I not spray pesticide?"}).get_json()
    assert body["mode"] == "passages"
    assert body["notice"] == "The assistant could not be reached."
    assert body["passages"]


def test_system_prompt_names_the_helpline_and_restricts_to_passages():
    assert "1800-180-1551" in chat.SYSTEM_PROMPT
    assert "Answer from the reference passages" in chat.SYSTEM_PROMPT
