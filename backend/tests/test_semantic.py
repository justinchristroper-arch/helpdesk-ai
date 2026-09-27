import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")
from types import SimpleNamespace
import numpy as np
import pytest
from app import embeddings, semantic
from app.intents import dataset


def test_dataset_is_diverse_and_source_backed():
    intents, digest = dataset()
    assert len(intents) == 18
    assert len(digest) == 64
    queries = [q for i in intents.values() for q in [i["canonical_question"], *i["paraphrases"]]]
    assert len(queries) == len(set(queries)) == 180
    assert sum(len(i["negative_examples"]) for i in intents.values()) == 54
    assert len({e["filename"] for i in intents.values() for e in i["evidence"]}) == 8


@pytest.mark.parametrize("vectors", [[[0.0]*384], [[float("nan")]*384], [[0.1]*20]])
def test_invalid_local_vectors_rejected(monkeypatch, vectors):
    monkeypatch.setattr(embeddings, "local_model", lambda: SimpleNamespace(embed=lambda *a, **k: [np.array(v) for v in vectors]))
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.embed(["vpn"])


def test_embedding_order_and_empty_input(monkeypatch):
    monkeypatch.setattr(embeddings, "local_model", lambda: SimpleNamespace(embed=lambda *a, **k: [np.array([0.1]*384), np.array([0.2]*384)]))
    assert embeddings.embed([]) == []
    assert embeddings.embed(["first", "second"])[1][0] == 0.2


def test_followup_uses_topic_but_topic_switch_does_not():
    context = {"active_intent": "vpn_request"}
    assert semantic.resolve_query("What are the requirements?", context)[1]
    assert not semantic.resolve_query("My laptop is damaged", context)[1]
    assert not semantic.resolve_query("What are the requirements?", None)[1]


@pytest.mark.parametrize("kind", ["procedure", "policy", "troubleshooting", "sla", "checklist", "approval", "requirements"])
def test_composer_facts_and_deterministic_presentation(kind):
    fact = "Manager approval is required before access."
    sources = [(SimpleNamespace(content=fact, section="Requirements"), SimpleNamespace(title="Policy"), .9, [fact])]
    answer = semantic.compose({"answer_type": kind}, sources, "request access")
    assert answer == semantic.compose({"answer_type": kind}, sources, "request access")
    assert fact + " [1]" in answer
    sources[0][3][0] = "An invented approval exception."
    with pytest.raises(ValueError):
        semantic.compose({"answer_type": kind}, sources, "request access")


def test_typos_are_normalized_without_exact_question_rules():
    assert semantic.normalize(" VPM   conection ERROR ") == "vpn connection error"


def test_embedding_module_has_no_external_api_client():
    import inspect
    source = inspect.getsource(embeddings)
    assert "TextEmbedding" in source and "local_files_only=True" in source
    assert "httpx" not in source and "api_key" not in source
