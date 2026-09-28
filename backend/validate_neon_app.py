"""Local FastAPI-to-Neon smoke flow with exact synthetic-row cleanup."""
import json
import os

os.environ["MINDROUTER_API_KEY"] = ""

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.config import get_settings
from app.db import Session
from app.main import app
from app.models import Conversation, Feedback, Message, MessageSource, User


def main():
    if os.getenv("VERIFY_NEON") != "1":
        raise SystemExit("Set VERIFY_NEON=1 to run the local API against Neon.")
    if not get_settings().database_url.startswith("postgresql+psycopg://"):
        raise SystemExit("Configured database is not using psycopg3.")

    user_id = conversation_id = None
    report = {}
    try:
        with TestClient(app, client=("127.0.0.9", 50000)) as client:
            health = client.get("/health")
            assert health.status_code == 200 and health.json()["status"] == "ok"
            assert health.json()["optional_synthesis"] == "disabled"

            guest = client.post("/auth/guest")
            assert guest.status_code == 201
            guest_body = guest.json()
            headers = {"Authorization": "Bearer " + guest_body["token"]}
            with Session() as db:
                user_id = db.scalar(select(User.id).where(User.email == guest_body["email"]))

            chat = client.post("/chat", headers=headers, json={
                "question": "My MFA is broken while I'm working remotely. What should I do?"})
            assert chat.status_code == 200
            body = chat.json()
            conversation_id = body["conversation_id"]
            message = body["message"]
            assert message["outcome"] == "answered"
            assert message["synthesis_status"] == "disabled"
            assert len(message["sources"]) == 2

            feedback = client.put("/messages/" + message["id"] + "/feedback",
                                  headers=headers, json={"rating": 1, "note": "Synthetic Neon validation"})
            assert feedback.status_code == 200
            history = client.get("/conversations/" + conversation_id, headers=headers)
            assert history.status_code == 200 and len(history.json()) == 2

            with Session() as db:
                source_count = db.scalar(select(func.count()).select_from(MessageSource)
                    .where(MessageSource.message_id == message["id"]))
                feedback_count = db.scalar(select(func.count()).select_from(Feedback)
                    .where(Feedback.message_id == message["id"]))
                persisted_conversation = db.get(Conversation, conversation_id) is not None
                sources_map = all(source["chunk_id"] and source["document_id"]
                                  and source["excerpt"] for source in message["sources"])

            report = {
                "health": "passed",
                "guest_auth": "passed",
                "chat": "passed",
                "outcome": message["outcome"],
                "intent": message["intent_id"],
                "mindrouter_disabled": message["synthesis_status"] == "disabled",
                "citations": len(message["sources"]),
                "citation_metadata_complete": sources_map,
                "conversation_persisted": persisted_conversation,
                "history_messages": len(history.json()),
                "feedback_persisted": feedback_count == 1,
                "message_sources_persisted": source_count == 2,
            }
    finally:
        if user_id:
            with Session.begin() as db:
                conversation_ids = list(db.scalars(select(Conversation.id)
                    .where(Conversation.user_id == user_id)))
                message_ids = list(db.scalars(select(Message.id)
                    .where(Message.conversation_id.in_(conversation_ids)))) if conversation_ids else []
                if message_ids:
                    db.execute(delete(Feedback).where(Feedback.message_id.in_(message_ids)))
                    db.execute(delete(MessageSource).where(MessageSource.message_id.in_(message_ids)))
                    db.execute(delete(Message).where(Message.id.in_(message_ids)))
                if conversation_ids:
                    db.execute(delete(Conversation).where(
                        Conversation.id.in_(conversation_ids), Conversation.user_id == user_id))
                db.execute(delete(User).where(User.id == user_id,
                                              User.email.like("guest-%@demo.invalid")))
            report["temporary_rows_cleaned"] = True

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
