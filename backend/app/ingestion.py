"""Pure extraction and token chunking; no provider or database side effects."""
import io
import re
from dataclasses import dataclass
from pathlib import PurePath

import tiktoken
from pypdf import PdfReader


class InvalidDocument(ValueError):
    pass


@dataclass(frozen=True)
class Passage:
    content: str
    page: int | None = None
    section: str | None = None


def extract(filename: str, data: bytes, max_bytes: int = 10 * 1024 * 1024) -> list[Passage]:
    if not data or len(data) > max_bytes:
        raise InvalidDocument("Upload must contain between 1 byte and 10 MB.")
    extension = PurePath(filename).suffix.lower()
    if extension not in {".pdf", ".txt", ".md"}:
        raise InvalidDocument("Supported files: PDF, TXT, Markdown.")
    passages: list[Passage] = []
    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise InvalidDocument("Invalid PDF signature.")
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise InvalidDocument("Encrypted PDFs are unsupported.")
            if len(reader.pages) > 200:
                raise InvalidDocument("Maximum 200 PDF pages.")
            passages = [Passage(page.extract_text() or "", index + 1) for index, page in enumerate(reader.pages)]
        except InvalidDocument:
            raise
        except Exception as exc:
            raise InvalidDocument("The PDF could not be read.") from exc
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidDocument("Text files must use UTF-8.") from exc
        if "\x00" in text:
            raise InvalidDocument("Binary content is unsupported.")
        section = None
        lines: list[str] = []
        for line in text.splitlines():
            if extension == ".md" and re.match(r"^#{1,6}\s+", line):
                if lines:
                    passages.append(Passage("\n".join(lines), section=section))
                section = line.lstrip("# ").strip()
                lines = [line]
            else:
                lines.append(line)
        if lines:
            passages.append(Passage("\n".join(lines), section=section))
    normalized = [Passage(re.sub(r"[ \t]+", " ", p.content).strip(), p.page, p.section) for p in passages]
    normalized = [p for p in normalized if p.content]
    if not normalized:
        raise InvalidDocument("No extractable text found. Scanned PDFs require OCR, which is not supported.")
    if sum(len(p.content) for p in normalized) > 1_000_000:
        raise InvalidDocument("Extracted text exceeds the processing limit.")
    return normalized


def chunk(passages: list[Passage], size: int = 700, overlap: int = 100) -> list[Passage]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")
    encoder = tiktoken.get_encoding("cl100k_base")
    chunks = []
    for passage in passages:
        tokens = encoder.encode(passage.content, disallowed_special=())
        for start in range(0, len(tokens), size - overlap):
            chunks.append(Passage(encoder.decode(tokens[start:start + size]), passage.page, passage.section))
            if start + size >= len(tokens):
                break
    return chunks
