"""
tests/test_validation.py
Unit tests for input validation utilities.
"""
import pytest

from src.exceptions import FileTooLargeError, InsufficientExplanationError, UnsupportedFileTypeError
from src.validation import (
    MAX_FILE_SIZE_BYTES,
    validate_room_code,
    validate_text_input,
    validate_upload,
)


class TestValidateUpload:
    def test_valid_pdf(self):
        validate_upload("notes.pdf", 1000)  # Should not raise

    def test_valid_txt(self):
        validate_upload("syllabus.txt", 500)  # Should not raise

    def test_uppercase_extension(self):
        validate_upload("Notes.PDF", 1000)  # Should not raise

    def test_unsupported_docx(self):
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload("notes.docx", 1000)

    def test_unsupported_jpg(self):
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload("image.jpg", 1000)

    def test_file_too_large(self):
        with pytest.raises(FileTooLargeError):
            validate_upload("big.pdf", MAX_FILE_SIZE_BYTES + 1)

    def test_exactly_at_limit_ok(self):
        validate_upload("ok.txt", MAX_FILE_SIZE_BYTES)  # Should not raise


class TestValidateTextInput:
    def test_valid_input(self):
        validate_text_input("This is a valid question.")  # Should not raise

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_text_input("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_text_input("   ")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="exceeds"):
            validate_text_input("x" * 1001, max_chars=1000)

    def test_exactly_at_limit_ok(self):
        validate_text_input("x" * 1000, max_chars=1000)  # Should not raise

    def test_below_min_words_raises(self):
        with pytest.raises(InsufficientExplanationError):
            validate_text_input("Too short", min_words=30)

    def test_meets_min_words_ok(self):
        text = " ".join(["word"] * 30)
        validate_text_input(text, min_words=30)  # Should not raise


class TestValidateRoomCode:
    def test_valid_code(self):
        validate_room_code("ABC123")  # Should not raise

    def test_lowercase_code(self):
        validate_room_code("abc123")  # Should not raise (isalnum works on lower)

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            validate_room_code("ABC")

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_room_code("ABC1234")

    def test_special_chars_raises(self):
        with pytest.raises(ValueError):
            validate_room_code("AB-123")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_room_code("")
