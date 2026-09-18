"""
tests/test_document_ingestion.py
Unit tests for document parsing, chunking, and retrieval.
No LLM calls — pure document processing logic.
"""
import pytest

from src.document_ingestion import (
    _chunk_by_words,
    _is_heading,
    chunk_document,
    extract_text_from_txt,
    retrieve_relevant_chunks,
    upload_and_parse,
)
from src.exceptions import (
    DuplicateDocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from src.models import Chunk, Document


# ---------------------------------------------------------------------------
# _is_heading
# ---------------------------------------------------------------------------

class TestIsHeading:
    def test_chapter_heading(self):
        assert _is_heading("Chapter 1 Introduction") is True

    def test_section_heading(self):
        assert _is_heading("Section 2.3 Methods") is True

    def test_numbered_heading(self):
        assert _is_heading("1.2 Background") is True

    def test_allcaps_heading(self):
        assert _is_heading("INTRODUCTION") is True

    def test_markdown_heading(self):
        assert _is_heading("## Results and Discussion") is True

    def test_normal_sentence_not_heading(self):
        assert _is_heading("The mitochondria is the powerhouse of the cell.") is False

    def test_empty_string_not_heading(self):
        assert _is_heading("") is False

    def test_too_short_not_heading(self):
        assert _is_heading("AB") is False


# ---------------------------------------------------------------------------
# extract_text_from_txt
# ---------------------------------------------------------------------------

class TestExtractTextFromTxt:
    def test_utf8_text(self):
        content = "Hello World\nThis is a test."
        result = extract_text_from_txt(content.encode("utf-8"))
        assert "Hello World" in result

    def test_latin1_fallback(self):
        content = b"caf\xe9"  # Latin-1 encoded bytes
        result = extract_text_from_txt(content)
        assert len(result) > 0

    def test_empty_raises(self):
        with pytest.raises(EmptyDocumentError):
            extract_text_from_txt(b"   \n\t  ")


# ---------------------------------------------------------------------------
# _chunk_by_words
# ---------------------------------------------------------------------------

class TestChunkByWords:
    def _make_doc(self) -> Document:
        return Document(doc_id="test-id", file_name="test.txt", file_type="txt")

    def test_single_chunk_short_text(self):
        doc = self._make_doc()
        doc.raw_text = "word " * 100
        chunks = _chunk_by_words(doc.doc_id, doc.raw_text, words_per_chunk=500)
        assert len(chunks) == 1

    def test_multiple_chunks_long_text(self):
        doc = self._make_doc()
        doc.raw_text = "word " * 1500
        chunks = _chunk_by_words(doc.doc_id, doc.raw_text, words_per_chunk=500)
        assert len(chunks) == 3

    def test_chunks_have_doc_id(self):
        doc = self._make_doc()
        doc.raw_text = "word " * 200
        chunks = _chunk_by_words(doc.doc_id, doc.raw_text)
        for chunk in chunks:
            assert chunk.doc_id == "test-id"

    def test_empty_text_yields_no_chunks(self):
        chunks = _chunk_by_words("id", "")
        assert len(chunks) == 0


# ---------------------------------------------------------------------------
# chunk_document
# ---------------------------------------------------------------------------

class TestChunkDocument:
    def test_falls_back_to_word_chunking(self):
        doc = Document(
            doc_id="doc-1",
            file_name="plain.txt",
            file_type="txt",
            raw_text="This is just regular text. " * 100,
        )
        chunks = chunk_document(doc)
        assert len(chunks) >= 1

    def test_headings_produce_named_chunks(self):
        doc = Document(
            doc_id="doc-2",
            file_name="headings.txt",
            file_type="txt",
            raw_text="Chapter 1 Introduction\nSome content here.\n\nChapter 2 Methods\nMore content here.",
        )
        page_texts = [(1, doc.raw_text)]
        chunks = chunk_document(doc, page_texts=page_texts)
        headings = [c.section_heading for c in chunks]
        assert any("Chapter" in h for h in headings)


# ---------------------------------------------------------------------------
# retrieve_relevant_chunks
# ---------------------------------------------------------------------------

class TestRetrieveRelevantChunks:
    def _make_chunks(self) -> list:
        return [
            Chunk(doc_id="d", page_number=1, section_heading="Photosynthesis",
                  content="Plants use sunlight water and carbon dioxide to produce glucose."),
            Chunk(doc_id="d", page_number=2, section_heading="Respiration",
                  content="Cells use oxygen to break down glucose and release energy as ATP."),
            Chunk(doc_id="d", page_number=3, section_heading="DNA Replication",
                  content="DNA double helix unwinds and each strand acts as a template."),
        ]

    def test_returns_most_relevant(self):
        chunks = self._make_chunks()
        results = retrieve_relevant_chunks("photosynthesis glucose plants", chunks, top_k=1)
        assert len(results) == 1
        assert results[0].section_heading == "Photosynthesis"

    def test_returns_empty_for_unrelated_query(self):
        chunks = self._make_chunks()
        results = retrieve_relevant_chunks("zzzzz xyzabc", chunks, top_k=3, min_score=0.05)
        assert results == []

    def test_top_k_limits_results(self):
        chunks = self._make_chunks()
        results = retrieve_relevant_chunks("glucose energy cells", chunks, top_k=2)
        assert len(results) <= 2

    def test_empty_query_returns_empty(self):
        chunks = self._make_chunks()
        results = retrieve_relevant_chunks("", chunks)
        assert results == []


# ---------------------------------------------------------------------------
# upload_and_parse
# ---------------------------------------------------------------------------

class TestUploadAndParse:
    def test_unsupported_type_raises(self):
        with pytest.raises(UnsupportedFileTypeError):
            upload_and_parse("notes.docx", b"content")

    def test_file_too_large_raises(self):
        big_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        with pytest.raises(FileTooLargeError):
            upload_and_parse("notes.txt", big_content)

    def test_empty_txt_raises(self):
        with pytest.raises(EmptyDocumentError):
            upload_and_parse("empty.txt", b"   ")

    def test_duplicate_raises(self):
        content = b"Some valid text content with enough words to pass."
        doc = upload_and_parse("file.txt", content)
        with pytest.raises(DuplicateDocumentError):
            upload_and_parse("file2.txt", content, existing_hashes=[doc.content_hash])

    def test_valid_txt_returns_document(self):
        content = b"Chapter 1\nThis is the introduction.\n" * 20
        doc = upload_and_parse("notes.txt", content)
        assert doc.file_name == "notes.txt"
        assert doc.file_type == "txt"
        assert len(doc.chunks) >= 1
        assert doc.content_hash != ""
