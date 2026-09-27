"""Opt-in two-call validation using only bundled synthetic knowledge.

Run with RUN_LIVE_MINDROUTER=1. Output contains questions/answers/citations,
never credentials or provider response bodies. Do not run in automated tests.
"""
import json
import os
import re
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import Session
from app.main import app
from app.models import Chunk, Document, Message, MessageSource

if os.getenv("RUN_LIVE_MINDROUTER") != "1":
    raise SystemExit("Set RUN_LIVE_MINDROUTER=1 to authorize exactly two live calls.")

settings = get_settings()
if not settings.mindrouter_api_key or not settings.mindrouter_api_key.get_secret_value():
    raise SystemExit("MindRouter key is absent; no external call made.")

questions = [
    "My MFA is broken while I'm working remotely. What should I do?",
    "The laptop assigned to me has stopped working safely while I am traveling; how should I report the damage and arrange help from IT?",
]
external_calls = 0
original_post = httpx.Client.post
api_prefix = settings.mindrouter_base_url.rstrip("/") + "/chat/completions"


def counted_post(self, url, *args, **kwargs):
    global external_calls
    if str(url) == api_prefix:
        external_calls += 1
    return original_post(self, url, *args, **kwargs)


def inspect_answer(message_id):
    with Session() as db:
        message = db.get(Message, message_id)
        sources = list(db.query(MessageSource).filter_by(message_id=message_id).order_by(MessageSource.citation_number))
        citations = []
        for source in sources:
            chunk = db.get(Chunk, source.chunk_id)
            document = db.get(Document, source.document_id)
            mapped = bool(chunk and document and document.status == "ready"
                          and chunk.document_id == document.id and source.excerpt == chunk.content)
            citations.append({"number": source.citation_number, "document": source.title,
                              "section": source.section, "chunk_id": source.chunk_id,
                              "maps_to_retrieved_chunk": mapped})
        number_to_source = {source.citation_number: source for source in sources}
        facts_map = True
        for line in message.content.splitlines():
            match = re.search(r"\[(\d+)\]$", line)
            if not match:
                continue
            number = int(match.group(1))
            fact = re.sub(r"^(?:•\s*|\d+\.\s*)", "", line[:match.start()].strip())
            if number not in number_to_source or fact not in number_to_source[number].excerpt:
                facts_map = False
        diagnostic = (message.diagnostics or {}).get("generation") or {}
        return {"mindrouter_called": diagnostic.get("called", False),
                "requested_model": settings.mindrouter_model,
                "returned_model": diagnostic.get("response_model"),
                "answer_model": message.model,
                "http_status": diagnostic.get("http_status"),
                "http_success": diagnostic.get("http_success"),
                "input_tokens": diagnostic.get("input_tokens"),
                "output_tokens": diagnostic.get("output_tokens"),
                "generation_state": diagnostic.get("state"),
                "answer": message.content, "citations": citations,
                "all_citations_map_to_retrieved_chunks": bool(citations) and all(c["maps_to_retrieved_chunk"] for c in citations) and facts_map}


results = []
with patch.object(httpx.Client, "post", counted_post):
    with TestClient(app) as client:
        for number, question in enumerate(questions, 1):
            guest = client.post("/auth/guest")
            assert guest.status_code == 201
            reply = client.post("/chat", headers={"Authorization": "Bearer " + guest.json()["token"]},
                                json={"question": question})
            assert reply.status_code == 200
            item = inspect_answer(reply.json()["message"]["id"])
            item.update({"test": number, "question": question, "external_calls_after_test": external_calls})
            results.append(item)

report = {"provider": "mindrouter", "external_calls_total": external_calls,
          "tests": results, "synthetic_data_only": True}
print(json.dumps(report, indent=2))
if external_calls != 2 or any(not item["mindrouter_called"] or not item["all_citations_map_to_retrieved_chunks"] for item in results):
    raise SystemExit(1)
