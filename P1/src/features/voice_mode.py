"""
src/features/voice_mode.py
Low-bandwidth voice-based doubt solving.
Handles STT (speech-to-text) and TTS (text-to-speech) with graceful fallback.
"""
from __future__ import annotations

import io
import os
from typing import Optional

from src.exceptions import STTFailureError

_MAX_TTS_CHARS = 500  # Limit TTS to first 500 chars to keep audio short


def transcribe_audio(audio_bytes: bytes, language: str = "en-US") -> str:
    """
    Convert audio bytes to text using the SpeechRecognition library (Google STT).

    Args:
        audio_bytes: Raw audio data (WAV format preferred).
        language: BCP-47 language code.

    Returns:
        Transcribed text string.

    Raises:
        STTFailureError: if transcription fails or returns empty text.
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        audio_file = io.BytesIO(audio_bytes)

        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data, language=language)

        if not text or not text.strip():
            raise STTFailureError("Speech recognition returned empty text.")

        return text.strip()

    except STTFailureError:
        raise
    except Exception as exc:
        raise STTFailureError(
            f"Voice recognition failed: {exc}. "
            "Please type your question instead."
        ) from exc


def synthesize_speech(text: str, language: str = "en") -> bytes:
    """
    Convert text to speech using gTTS (Google Text-to-Speech).

    Args:
        text: The text to speak (truncated to _MAX_TTS_CHARS).
        language: Language code for TTS.

    Returns:
        MP3 audio bytes.

    Raises:
        Exception: if TTS fails (caller handles gracefully).
    """
    truncated = text[:_MAX_TTS_CHARS]
    if not truncated.strip():
        raise ValueError("Cannot synthesize empty text.")

    try:
        from gtts import gTTS

        tts = gTTS(text=truncated, lang=language, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception as exc:
        raise RuntimeError(f"Text-to-speech failed: {exc}") from exc
