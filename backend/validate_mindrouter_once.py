"""Exactly one final HelpDesk synthesis request after local payload correction."""
import json
import os
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.generation import sanitized_error_shape
from app.db import Session
from app.main import app
from app.models import Chunk, Document, Message, MessageSource

if os.getenv("RUN_ONE_MINDROUTER_VALIDATION") != "1":
    raise SystemExit("Set RUN_ONE_MINDROUTER_VALIDATION=1 to authorize exactly one final call.")

settings = get_settings()
if settings.mindrouter_model != "openai/gpt-4.1-nano" or settings.mindrouter_max_output_tokens != 300:
    raise SystemExit("Validation requires GPT-4.1 Nano and a 300-token ceiling.")
external_calls = 0
safe_http_error = None
original_post = httpx.Client.post
url = settings.mindrouter_base_url.rstrip("/") + "/chat/completions"


def counted_post(self, target, *args, **kwargs):
    global external_calls, safe_http_error
    if str(target) == url:
        if external_calls >= 1:
            raise RuntimeError("One-call validation budget exhausted")
        if set(kwargs.get("json", {})) != {"model", "messages", "max_tokens"}:
            raise RuntimeError("Unexpected generation request fields")
        external_calls += 1
    response = original_post(self, target, *args, **kwargs)
    if str(target) == url and not response.is_success:
        safe_http_error = sanitized_error_shape(response)
    return response


question = "My MFA is broken while I'm working remotely. What should I do?"
with patch.object(httpx.Client, "post", counted_post):
    # Use a dedicated synthetic validation address so earlier provider diagnostics
    # do not bypass or erase the persisted per-IP quota history.
    with TestClient(app, client=("127.0.0.2", 50000)) as client:
        guest = client.post("/auth/guest")
        reply = client.post("/chat", headers={"Authorization": "Bearer " + guest.json()["token"]},
                            json={"question": question})
        assert reply.status_code == 200
        message_id = reply.json()["message"]["id"]

with Session() as db:
    message = db.get(Message, message_id)
    sources = list(db.scalars(select(MessageSource).where(MessageSource.message_id == message_id)
                              .order_by(MessageSource.citation_number)))
    citations = []
    for source in sources:
        chunk = db.get(Chunk, source.chunk_id)
        document = db.get(Document, source.document_id)
        citations.append({"number": source.citation_number, "document": source.title,
                          "section": source.section, "chunk_id": source.chunk_id,
                          "maps_to_postgres_chunk": bool(chunk and document and document.status == "ready"
                              and chunk.document_id == document.id and chunk.content == source.excerpt)})
    generation = (message.diagnostics or {}).get("generation") or {}
    report = {"external_calls": external_calls, "question": question,
              "requested_model": settings.mindrouter_model,
              "http_status": generation.get("http_status"),
              "reported_model": generation.get("response_model"),
              "input_tokens": generation.get("input_tokens"),
              "output_tokens": generation.get("output_tokens"),
              "reasoning_tokens": generation.get("reasoning_tokens"),
              "finish_reason": generation.get("finish_reason"),
              "visible_content_length": (generation.get("response_shape") or {}).get("content_length"),
              "referenced_fact_ids": generation.get("referenced_fact_ids"),
              "validation_reason": generation.get("validation_reason"),
              "synthesis_used": generation.get("state") == "used" and message.model == settings.mindrouter_model,
              "deterministic_fallback": message.model != settings.mindrouter_model,
              "final_public_answer": message.content,
              "sanitized_response_structure": generation.get("response_shape"),
              "sanitized_http_error": safe_http_error,
              "citations": citations}
print(json.dumps(report, indent=2))
if external_calls != 1:
    raise SystemExit("Expected exactly one external call")
