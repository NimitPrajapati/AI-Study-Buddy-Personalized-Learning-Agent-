"""
src/persistence.py
Lightweight JSON-based persistence for user progress, quiz history,
and uploaded content metadata. Falls back gracefully when file I/O fails.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_PROGRESS_FILE = os.path.join(_DATA_DIR, "progress.json")


def _ensure_data_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _serialize(obj: Any) -> Any:
    """Make common non-serialisable types JSON-safe."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def save_progress(user_id: str, data: Dict[str, Any]) -> None:
    """
    Persist a user's progress snapshot to data/progress.json.
    Silently ignores I/O errors so the app never crashes on save.
    """
    try:
        _ensure_data_dir()
        existing: Dict[str, Any] = {}
        if os.path.exists(_PROGRESS_FILE):
            with open(_PROGRESS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing[user_id] = _serialize(data)
        with open(_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass  # Non-critical — session_state is the primary store


def load_progress(user_id: str) -> Dict[str, Any]:
    """
    Load a user's previously saved progress snapshot.
    Returns an empty dict if nothing is found.
    """
    try:
        if os.path.exists(_PROGRESS_FILE):
            with open(_PROGRESS_FILE, "r", encoding="utf-8") as f:
                all_data: Dict[str, Any] = json.load(f)
            return all_data.get(user_id, {})
    except Exception:
        pass
    return {}


def save_document_metadata(doc_meta_list: List[Dict[str, Any]]) -> None:
    """
    Persist lightweight document metadata (name, hash, upload time) to disk.
    """
    try:
        _ensure_data_dir()
        path = os.path.join(_DATA_DIR, "documents.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_serialize(doc_meta_list), f, indent=2)
    except Exception:
        pass


def load_document_metadata() -> List[Dict[str, Any]]:
    """Return previously saved document metadata or empty list."""
    try:
        path = os.path.join(_DATA_DIR, "documents.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []
