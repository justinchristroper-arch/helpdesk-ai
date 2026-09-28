"""Vercel entrypoint: mount the authoritative API without duplicating routes."""
import os
from pathlib import Path

from fastapi import FastAPI

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("EMBEDDING_CACHE_DIR", "/tmp/helpdesk-fastembed")
os.environ.setdefault("EMBEDDING_MODEL_PATH", str(ROOT / "model-cache"))
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(ROOT / "tokenizer-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from app.main import app as backend_app

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", backend_app)
