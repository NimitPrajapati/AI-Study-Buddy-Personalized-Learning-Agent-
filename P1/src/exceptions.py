"""
src/exceptions.py
Custom exception hierarchy for the AI Study Buddy application.
"""


class StudyBuddyError(Exception):
    """Base exception for all application errors."""


class UnsupportedFileTypeError(StudyBuddyError):
    """Raised when a file with an unsupported extension is uploaded."""


class FileTooLargeError(StudyBuddyError):
    """Raised when an uploaded file exceeds the maximum allowed size."""


class EmptyDocumentError(StudyBuddyError):
    """Raised when a parsed document yields no extractable text."""


class DuplicateDocumentError(StudyBuddyError):
    """Raised when the same file (by content hash) is uploaded more than once."""


class ChunkingFailureError(StudyBuddyError):
    """Raised when document chunking produces zero usable chunks."""


class OutOfScopeQueryError(StudyBuddyError):
    """Raised when a chatbot query cannot be answered from the uploaded notes."""


class NoCitationFoundError(StudyBuddyError):
    """Raised when an LLM answer is generated but no source chunk can be linked."""


class WatsonxAPIError(StudyBuddyError):
    """Raised when the IBM watsonx.ai SDK returns an error or non-200 response."""


class RoomNotFoundError(StudyBuddyError):
    """Raised when a multiplayer room code does not exist."""


class RoomFullError(StudyBuddyError):
    """Raised when a multiplayer room has reached its maximum participant count."""


class QuizNotStartedError(StudyBuddyError):
    """Raised when an answer is submitted before the quiz is in 'active' status."""


class STTFailureError(StudyBuddyError):
    """Raised when speech-to-text transcription fails or returns empty text."""


class InsufficientExplanationError(StudyBuddyError):
    """Raised when a Reverse Learning input is too short to evaluate (< 30 words)."""
