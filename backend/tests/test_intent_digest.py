"""The reviewed intent index must have one version on Windows and Linux."""

from app import intents


def test_intent_dataset_hash_ignores_checkout_line_endings(tmp_path, monkeypatch):
    source = tmp_path / "intents.json"
    document = b'{\n  "intents": []\n}\n'
    monkeypatch.setattr(intents, "DATA_PATH", source)
    try:
        source.write_bytes(document)
        intents.dataset.cache_clear()
        lf_hash = intents.dataset()[1]

        source.write_bytes(document.replace(b"\n", b"\r\n"))
        intents.dataset.cache_clear()
        assert intents.dataset()[1] == lf_hash
    finally:
        intents.dataset.cache_clear()
