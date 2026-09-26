FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
ENV TIKTOKEN_CACHE_DIR=/app/tokenizer-cache
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
COPY . .
ENV EMBEDDING_CACHE_DIR=/app/model-cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/app/model-cache')"
RUN useradd --create-home appuser
RUN chown -R appuser:appuser /app/model-cache
USER appuser
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
