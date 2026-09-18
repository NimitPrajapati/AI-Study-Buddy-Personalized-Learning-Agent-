"""
src/document_ingestion.py
Upload validation, text extraction, chunking, deduplication, and retrieval.
This module has NO dependency on the LLM — it is purely document processing.
"""
from __future__ import annotations

import hashlib
import re
from typing import List, Optional, Tuple

from src.exceptions import (
    ChunkingFailureError,
    DuplicateDocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from src.models import Chunk, Document
from src.validation import MAX_FILE_SIZE_BYTES, ALLOWED_FILE_EXTENSIONS

_WORDS_PER_CHUNK = 500
_MIN_HEADING_LENGTH = 3
_MAX_HEADING_LENGTH = 80

# Patterns that look like section headings
_HEADING_PATTERNS = [
    re.compile(r"^(Chapter|Section|Unit|Topic|Part|Module)\s+[\dIVXivx]+", re.IGNORECASE),
    re.compile(r"^\d+(\.\d+)*\s+[A-Z]"),          # "1.2 Introduction"
    re.compile(r"^[A-Z][A-Z\s]{4,}$"),             # ALL-CAPS line
    re.compile(r"^#{1,3}\s+\S"),                   # Markdown headings
]


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < _MIN_HEADING_LENGTH or len(stripped) > _MAX_HEADING_LENGTH:
        return False
    return any(p.match(stripped) for p in _HEADING_PATTERNS)


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, List[Tuple[int, str]]]:
    """
    Extract text from a PDF file using PyMuPDF.

    Returns:
        (full_text, page_texts) where page_texts is a list of (page_number, text) tuples.

    Raises:
        EmptyDocumentError: if the PDF contains no extractable text (likely scanned).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError("PyMuPDF (fitz) is required for PDF parsing.") from exc

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise EmptyDocumentError(f"Could not open PDF: {exc}") from exc

    page_texts: List[Tuple[int, str]] = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            page_texts.append((page_num + 1, text))

    doc.close()

    if not page_texts:
        raise EmptyDocumentError(
            "No text could be extracted from this PDF. "
            "It may be a scanned image. Please use a text-based PDF or convert it first."
        )

    full_text = "\n".join(t for _, t in page_texts)
    return full_text, page_texts


def extract_text_from_txt(file_bytes: bytes) -> str:
    """
    Decode a TXT file to string.

    Raises:
        EmptyDocumentError: if the file is empty after stripping whitespace.
    """
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1", errors="replace")

    if not text.strip():
        raise EmptyDocumentError("The uploaded text file is empty.")
    return text


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_by_headings(doc_id: str, page_texts: List[Tuple[int, str]]) -> List[Chunk]:
    """Split text into chunks using detected headings as boundaries."""
    chunks: List[Chunk] = []
    current_heading = "Introduction"
    current_page = 1
    current_lines: List[str] = []

    def _flush(heading: str, page: int, lines: List[str]) -> None:
        content = "\n".join(lines).strip()
        if content:
            chunks.append(Chunk(
                doc_id=doc_id,
                page_number=page,
                section_heading=heading,
                content=content,
            ))

    for page_num, text in page_texts:
        for line in text.splitlines():
            if _is_heading(line):
                _flush(current_heading, current_page, current_lines)
                current_heading = line.strip()
                current_page = page_num
                current_lines = []
            else:
                current_lines.append(line)

    _flush(current_heading, current_page, current_lines)
    return chunks


def _chunk_by_words(doc_id: str, raw_text: str, words_per_chunk: int = _WORDS_PER_CHUNK) -> List[Chunk]:
    """Fall-back: split into fixed-size word windows."""
    words = raw_text.split()
    chunks: List[Chunk] = []
    for i in range(0, len(words), words_per_chunk):
        window = words[i: i + words_per_chunk]
        chunks.append(Chunk(
            doc_id=doc_id,
            page_number=0,
            section_heading=f"Section {len(chunks) + 1}",
            content=" ".join(window),
        ))
    return chunks


def chunk_document(doc: Document, page_texts: Optional[List[Tuple[int, str]]] = None) -> List[Chunk]:
    """
    Chunk a Document into retrievable Chunk objects.
    Tries heading-based splitting first; falls back to fixed-size windows.

    Raises:
        ChunkingFailureError: if no chunks could be produced.
    """
    if page_texts:
        chunks = _chunk_by_headings(doc.doc_id, page_texts)
        if chunks:
            return chunks

    # Fall back to word-window chunking
    chunks = _chunk_by_words(doc.doc_id, doc.raw_text)
    if not chunks:
        raise ChunkingFailureError(
            f"Could not split '{doc.file_name}' into chunks. "
            "The document may be too short or contain only non-text content."
        )
    return chunks


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def _score_chunk(query_words: set, chunk: Chunk) -> float:
    """Simple word-overlap score between query and chunk content."""
    chunk_words = set(chunk.content.lower().split())
    if not chunk_words:
        return 0.0
    intersection = query_words & chunk_words
    # Jaccard-like: intersection over union
    return len(intersection) / len(query_words | chunk_words)


def retrieve_relevant_chunks(
    query: str,
    chunks: List[Chunk],
    top_k: int = 3,
    min_score: float = 0.01,
) -> List[Chunk]:
    """
    Return the top-k most relevant chunks for a query using word-overlap scoring.

    Args:
        query: The user's question or topic.
        chunks: All chunks from the relevant document(s).
        top_k: Maximum number of chunks to return.
        min_score: Minimum overlap score to be considered relevant.

    Returns:
        Ordered list of most-relevant Chunk objects (best first).
        Returns empty list if no chunk meets the min_score threshold.
    """
    query_words = set(query.lower().split())
    if not query_words:
        return []

    scored = [(chunk, _score_chunk(query_words, chunk)) for chunk in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)

    results = [chunk for chunk, score in scored if score >= min_score]
    return results[:top_k]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def upload_and_parse(
    file_name: str,
    file_bytes: bytes,
    existing_hashes: Optional[List[str]] = None,
) -> Document:
    """
    Validate, extract, chunk, and return a Document object.

    Args:
        file_name: Original filename (used to detect type).
        file_bytes: Raw file content.
        existing_hashes: List of content hashes already in session to detect duplicates.

    Raises:
        UnsupportedFileTypeError, FileTooLargeError, EmptyDocumentError,
        DuplicateDocumentError, ChunkingFailureError.
    """
    # --- Validate ---
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File is {file_size / (1024*1024):.1f} MB. Maximum allowed is 10 MB."
        )

    lower_name = file_name.lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_FILE_EXTENSIONS):
        raise UnsupportedFileTypeError(
            f"'{file_name}' is not a supported format. Upload PDF or TXT only."
        )

    # --- Extract ---
    page_texts: Optional[List[Tuple[int, str]]] = None
    if lower_name.endswith(".pdf"):
        raw_text, page_texts = extract_text_from_pdf(file_bytes)
        file_type = "pdf"
    else:
        raw_text = extract_text_from_txt(file_bytes)
        file_type = "txt"

    # --- Deduplicate ---
    content_hash = _md5(raw_text)
    if existing_hashes and content_hash in existing_hashes:
        raise DuplicateDocumentError(
            f"'{file_name}' has already been uploaded (identical content detected)."
        )

    # --- Build document ---
    doc = Document(
        file_name=file_name,
        file_type=file_type,
        raw_text=raw_text,
        content_hash=content_hash,
    )

    # --- Chunk ---
    doc.chunks = chunk_document(doc, page_texts=page_texts)

    return doc
