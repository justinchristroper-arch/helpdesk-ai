from pathlib import PurePath
from hashlib import sha256
from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import embeddings, generation, semantic
from uuid import uuid4
from app.auth import admin, current_user, passwords, token_for
from app.config import get_settings
from app.db import get_db
from app.ingestion import InvalidDocument, chunk, extract
from app.limits import limit
from app.client_ip import client_ip
from app.models import Chunk, Conversation, Document, Feedback, Message, MessageSource, User, now

settings = get_settings()
app = FastAPI(title="HelpDesk AI", description="Portfolio demonstration. Synthetic IT policies only; not a production support service.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.exception_handler(embeddings.EmbeddingError)
async def provider_error(_, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(SQLAlchemyError)
async def database_error(_, exc):
    return JSONResponse(status_code=503, content={"detail": "Storage is temporarily unavailable."})


@app.exception_handler(InvalidDocument)
async def invalid_document(_, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class Rating(BaseModel):
    rating: Literal[-1, 1]
    note: str | None = Field(default=None, max_length=1000)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "inference": "local-fastembed", "external_ai_required": False, "optional_synthesis": "mindrouter" if settings.mindrouter_api_key else "disabled", "composer": semantic.VERSION}


@app.post("/auth/guest", status_code=201)
def guest(request: Request, db: Session = Depends(get_db)):
    limit("guest:" + client_ip(request), 15)
    user = User(email=f"guest-{uuid4().hex}@demo.invalid", password_hash="!", role="guest")
    db.add(user)
    db.commit()
    return {"token": token_for(user), "role": user.role, "email": user.email}


@app.post("/auth/login")
def login(body: Login, request: Request, db: Session = Depends(get_db)):
    limit("login:" + client_ip(request), 10)
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    if not user or user.role == "guest" or not passwords.verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password.")
    return {"token": token_for(user), "role": user.role, "email": user.email}


@app.get("/documents")
def documents(db: Session = Depends(get_db)):
    return list(db.scalars(select(Document).where(Document.status == "ready").order_by(Document.created_at.desc())))


@app.get("/documents/{document_id}")
def document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or doc.status != "ready":
        raise HTTPException(404, "Document not found.")
    chunks = db.scalars(select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index))
    return {"document": doc, "chunks": [{"id": c.id, "content": c.content, "section": c.section, "page_number": c.page_number} for c in chunks]}


@app.post("/documents", status_code=201)
def upload(file: UploadFile = File(...), user: User = Depends(admin), db: Session = Depends(get_db)):
    limit("upload:" + user.id, 10)
    filename = PurePath((file.filename or "document").replace("\\", "/")).name[:255]
    data = file.file.read(settings.max_upload_bytes + 1)
    passages = chunk(extract(filename, data, settings.max_upload_bytes), settings.chunk_tokens, settings.overlap_tokens)
    if len(passages) > 500:
        raise HTTPException(422, "Document exceeds the 500-chunk limit.")
    vectors = embeddings.embed([p.content for p in passages])
    mime = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}[PurePath(filename).suffix.lower()]
    doc = Document(title=PurePath(filename).stem[:200], filename=filename, mime_type=mime, embedding_model=settings.embedding_model, content_hash=sha256(data).hexdigest())
    db.add(doc)
    db.flush()
    for index, (passage, vector) in enumerate(zip(passages, vectors, strict=True)):
        db.add(Chunk(document_id=doc.id, chunk_index=index, content=passage.content, page_number=passage.page, section=passage.section, embedding=vector))
    db.commit()
    return doc


@app.delete("/documents/{document_id}", status_code=204)
def remove_document(document_id: str, user: User = Depends(admin), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    db.delete(doc)
    db.commit()


@app.post("/documents/{document_id}/reindex")
def reindex(document_id: str, user: User = Depends(admin), db: Session = Depends(get_db)):
    limit("upload:" + user.id, 10)
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    chunks = list(db.scalars(select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)))
    vectors = embeddings.embed([c.content for c in chunks])
    for item, vector in zip(chunks, vectors, strict=True):
        item.embedding = vector
    doc.embedding_model = settings.embedding_model
    doc.updated_at = now()
    db.commit()
    return {"chunks": len(chunks)}


def owned_conversation(db, conversation_id, user):
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(404, "Conversation not found.")
    return conversation


def serialize_message(db, message):
    sources = list(db.scalars(select(MessageSource).where(MessageSource.message_id == message.id, MessageSource.citation_number.is_not(None)).order_by(MessageSource.citation_number)))
    feedback_rating = db.scalar(select(Feedback.rating).where(Feedback.message_id == message.id)) if message.role == "assistant" else None
    state = ((message.diagnostics or {}).get("generation") or {}).get("state")
    synthesis_status = "used" if state == "used" else "limited" if state == "quota_or_storage" else "disabled" if state == "disabled" else "unavailable" if state else None
    return {"id": message.id, "role": message.role, "content": message.content, "outcome": message.outcome, "intent_id": message.intent_id, "clarification": message.clarification or [], "sources": sources, "synthesis_status": synthesis_status, "feedback_rating": feedback_rating}


@app.get("/conversations")
def conversations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())))


@app.get("/conversations/{conversation_id}")
def history(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_conversation(db, conversation_id, user)
    return [serialize_message(db, m) for m in db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at, Message.id))]


@app.post("/chat")
def chat(body: Question, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    question = body.question.strip()
    if not question:
        raise HTTPException(422, "Enter a question.")
    limit("chat:" + user.id, 10)
    conversation = owned_conversation(db, body.conversation_id, user) if body.conversation_id else None
    result = semantic.answer(db, question, conversation.context if conversation else None)
    model = settings.embedding_model
    if generation.should_synthesize(result, question):
        synthesis = generation.synthesize(question, result, user.id, client_ip(request))
        result.diagnostics["generation"] = synthesis.diagnostics()
        if synthesis.answer:
            result.content = synthesis.answer
            model = settings.mindrouter_model
    if conversation is None:
        conversation = Conversation(user_id=user.id, title=question[:120])
        db.add(conversation)
        db.flush()
    conversation.updated_at = now()
    conversation.context = result.context or (conversation.context if result.outcome == "clarification" else None)
    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    message = Message(conversation_id=conversation.id, role="assistant", content=result.content, outcome=result.outcome, model=model, prompt_version=semantic.VERSION, intent_id=result.intent_id, diagnostics=result.diagnostics, clarification=result.clarification)
    db.add(message)
    db.flush()
    for index, (c, d, score, facts) in enumerate(result.sources, 1):
        db.add(MessageSource(message_id=message.id, chunk_id=c.id, document_id=d.id, title=d.title, section=c.section, page_number=c.page_number, excerpt=c.content, relevance_score=float(score), citation_number=index))
    db.commit()
    return {"conversation_id": conversation.id, "message": serialize_message(db, message)}


@app.put("/messages/{message_id}/feedback")
def feedback(message_id: str, body: Rating, user: User = Depends(current_user), db: Session = Depends(get_db)):
    message = db.get(Message, message_id)
    if not message or message.role != "assistant":
        raise HTTPException(404, "Answer not found.")
    owned_conversation(db, message.conversation_id, user)
    rating = db.scalar(select(Feedback).where(Feedback.message_id == message_id, Feedback.user_id == user.id))
    if not rating:
        rating = Feedback(message_id=message_id, user_id=user.id)
        db.add(rating)
    rating.rating, rating.note = body.rating, body.note
    db.commit()
    return {"rating": rating.rating}


@app.get("/analytics")
def analytics(user: User = Depends(admin), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Message).where(Message.role == "assistant")) or 0
    answered = db.scalar(select(func.count()).select_from(Message).where(Message.outcome == "answered")) or 0
    clarified = db.scalar(select(func.count()).select_from(Message).where(Message.outcome == "clarification")) or 0
    intents = db.execute(select(Message.intent_id, func.count()).where(Message.intent_id.is_not(None)).group_by(Message.intent_id).order_by(func.count().desc()).limit(10)).all()
    unmatched_query = Message.diagnostics["resolved_query"].as_string()
    unmatched = db.execute(select(unmatched_query, func.count()).where(Message.outcome == "fallback", Message.diagnostics.is_not(None)).group_by(unmatched_query).order_by(func.count().desc()).limit(10)).all()
    ratings = db.scalar(select(func.count()).select_from(Feedback)) or 0
    positive = db.scalar(select(func.count()).select_from(Feedback).where(Feedback.rating == 1)) or 0
    synthesized = db.scalar(select(func.count()).select_from(Message).where(
        Message.role == "assistant", Message.outcome == "answered",
        Message.diagnostics["generation"]["state"].as_string() == "used")) or 0
    sources = db.execute(select(MessageSource.title, func.count().label("uses")).where(MessageSource.citation_number.is_not(None)).group_by(MessageSource.title).order_by(func.count().desc()).limit(10)).all()
    recent = db.execute(select(Message.content, Message.created_at).where(Message.role == "user").order_by(Message.created_at.desc()).limit(10)).all()
    return {"total_questions": total, "answered": answered, "deterministic_answers": answered - synthesized, "synthesized_answers": synthesized, "fallbacks": total - answered - clarified, "clarifications": clarified, "top_unmatched": [{"question": q, "count": n} for q,n in unmatched], "top_intents": [{"intent": i, "questions": n} for i, n in intents], "positive_feedback_percent": round(100 * positive / ratings, 1) if ratings else None, "feedback_count": ratings, "top_sources": [{"title": t, "uses": n} for t, n in sources], "recent_queries": [{"question": q, "created_at": t} for q, t in recent]}
