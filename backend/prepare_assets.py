"""Download immutable runtime assets at build time, never during public requests."""
import os
import shutil
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    os.environ["TIKTOKEN_CACHE_DIR"] = str(root / "tokenizer-cache")
    from fastembed import TextEmbedding
    from huggingface_hub import snapshot_download
    import tiktoken

    # The same quantized ONNX snapshot used by the verified Docker baseline.
    # Materialize only one copy; download-cache symlinks can inflate bundles.
    with tempfile.TemporaryDirectory() as cache:
        snapshot = snapshot_download(
            repo_id="Qdrant/bge-small-en-v1.5-onnx-Q",
            revision="aa8f8b060edb00e03bfdd08813a2949946c8ba55",
            cache_dir=cache,
            allow_patterns=["config.json", "tokenizer.json", "tokenizer_config.json",
                            "special_tokens_map.json", "model_optimized.onnx"],
        )
        shutil.copytree(snapshot, root / "model-cache", dirs_exist_ok=True)
    # Hub downloads can be owner-only; the runtime may use a different UID.
    (root / "model-cache").chmod(0o755)
    for asset in (root / "model-cache").rglob("*"):
        asset.chmod(0o755 if asset.is_dir() else 0o644)
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5",
                          specific_model_path=str(root / "model-cache"),
                          threads=2, local_files_only=True)
    vector = next(model.embed(["Synthetic IT support build verification."]))
    assert len(vector) == 384
    tiktoken.get_encoding("cl100k_base")
    for asset in (root / "tokenizer-cache").rglob("*"):
        asset.chmod(0o755 if asset.is_dir() else 0o644)
    total = sum(p.stat().st_size for directory in ("model-cache", "tokenizer-cache")
                for p in (root / directory).rglob("*") if p.is_file())
    print(f"Runtime assets prepared: {total} bytes; embedding dimensions: {len(vector)}")


if __name__ == "__main__":
    main()
