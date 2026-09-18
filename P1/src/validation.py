"""
src/validation.py
Shared input-validation utilities used across all pages and feature modules.
"""
from __future__ import annotations

from typing import Optional

from src.exceptions import (
    FileTooLargeError,
    InsufficientExplanationError,
    UnsupportedFileTypeError,
)

MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_EXTENSIONS: tuple = (".pdf", ".txt")
MAX_QUESTION_CHARS: int = 1000
MIN_RL_WORDS: int = 30

ALLOWED_PERSONAS: tuple = (
    "Professor",
    "Grandma",
    "Cricket Commentator",
    "Movie Dialogue",
    "ELI5 (Explain Like I'm 5)",
    "Sherlock Holmes",
    "Sports Coach",
)


def validate_upload(file_name: str, file_size: int) -> None:
    """
    Validate that an uploaded file has an allowed extension and is within size limits.

    Raises:
        UnsupportedFileTypeError: if the extension is not in ALLOWED_FILE_EXTENSIONS.
        FileTooLargeError: if the file exceeds MAX_FILE_SIZE_BYTES.
    """
    lower = file_name.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_FILE_EXTENSIONS):
        raise UnsupportedFileTypeError(
            f"'{file_name}' is not supported. Please upload a PDF or TXT file."
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        mb = file_size / (1024 * 1024)
        raise FileTooLargeError(
            f"File is {mb:.1f} MB. Maximum allowed size is 10 MB."
        )


def validate_text_input(
    text: str,
    min_words: int = 0,
    max_chars: int = MAX_QUESTION_CHARS,
    field_name: str = "Input",
) -> None:
    """
    Validate a text input for emptiness, length limits, and minimum word count.

    Raises:
        ValueError: if the text is empty or exceeds max_chars.
        InsufficientExplanationError: if word count is below min_words.
    """
    if not text or not text.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    if len(text) > max_chars:
        raise ValueError(
            f"{field_name} exceeds {max_chars} characters "
            f"(current: {len(text)} chars)."
        )
    if min_words > 0:
        word_count = len(text.split())
        if word_count < min_words:
            raise InsufficientExplanationError(
                f"{field_name} must be at least {min_words} words "
                f"(current: {word_count} words). Please explain in more detail."
            )


def validate_persona(persona: str) -> None:
    """
    Validate that the selected persona is from the fixed allowlist.

    Raises:
        ValueError: if persona is not in ALLOWED_PERSONAS.
    """
    if persona not in ALLOWED_PERSONAS:
        raise ValueError(
            f"Invalid persona '{persona}'. Choose from: {', '.join(ALLOWED_PERSONAS)}"
        )


def validate_room_code(code: str) -> None:
    """
    Validate a multiplayer room code (exactly 6 alphanumeric characters).

    Raises:
        ValueError: if code format is invalid.
    """
    if not code or len(code) != 6 or not code.isalnum():
        raise ValueError(
            "Room code must be exactly 6 alphanumeric characters (e.g., AB12CD)."
        )
