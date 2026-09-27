"""Real API + cold local embedding + PostgreSQL test with inference network blocked."""
import json
import os
import socket
import time
from unittest.mock import patch

for name in list(os.environ):
    if name.endswith("API_KEY"):
        os.environ.pop(name)
os.environ["DEEPSEEK_API_KEY"] = ""  # Override any local .env value for this offline proof.
os.environ["HF_HUB_OFFLINE"] = "1"
original_connect = socket.socket.connect
blocked = []


def local_database_only(sock, address):
    if isinstance(address, tuple) and address[1] == 5432:
        return original_connect(sock, address)
    blocked.append(str(address))
    raise AssertionError("Non-database outbound connection attempted")


with patch.object(socket.socket, "connect", local_database_only):
    from fastapi.testclient import TestClient
    from app.main import app
    started = time.perf_counter()
    with TestClient(app) as client:
        guest = client.post("/auth/guest")
        assert guest.status_code == 201
        headers = {"Authorization": "Bearer " + guest.json()["token"]}
        reply = client.post("/chat", headers=headers, json={"question": "How do I request VPN access?"})
        assert reply.status_code == 200, reply.text
        body = reply.json()
        assert body["message"]["outcome"] == "answered", body
        assert body["message"]["sources"] and "manager" in body["message"]["content"]
        assert client.put("/messages/"+body["message"]["id"]+"/feedback", headers=headers, json={"rating": 1}).status_code == 200
        assert len(client.get("/conversations/"+body["conversation_id"], headers=headers).json()) == 2
        fallback = client.post("/chat", headers=headers, json={"question": "What is the laptop reimbursement limit?"}).json()
        assert fallback["message"]["outcome"] == "fallback"
        follow = client.post("/chat", headers=headers, json={"question": "What are the requirements?", "conversation_id": body["conversation_id"]}).json()
        assert follow["message"]["intent_id"] == "vpn_request", follow
        multi = client.post("/chat", headers=headers, json={"question": "My MFA is broken while I'm working remotely. What should I do?"}).json()
        assert multi["message"]["outcome"] == "answered" and len(multi["message"]["sources"]) == 2
    assert not blocked, blocked
    print(json.dumps({"passed": True, "external_socket_attempts": len(blocked), "api_keys_present": False,
        "cold_api_flow_seconds": round(time.perf_counter()-started, 3), "checks": ["guest", "answer", "citations", "feedback", "history", "fallback", "followup", "multisource_no_key"]}))
