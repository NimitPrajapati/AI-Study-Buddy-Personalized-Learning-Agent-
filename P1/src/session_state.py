"""
src/session_state.py
Centralised Streamlit session_state initialisation.
Call init_session() at the top of every page.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    pass


def init_session() -> None:
    """
    Ensure all required session_state keys exist with their default values.
    Safe to call multiple times — only sets keys that are not yet present.
    """
    from src.models import UserProfile

    defaults: dict = {
        # Unique per-session user identity
        "user_id": str(uuid.uuid4()),
        # Uploaded study documents: List[Document]
        "documents": [],
        # Uploaded past exam papers: List[Document]
        "exam_papers": [],
        # Per-user learning profile
        "profile": UserProfile(),
        # Chatbot conversation history: List[{"role": str, "content": str}]
        "chat_history": [],
        # Multiplayer quiz rooms: Dict[room_code, QuizRoom]
        "rooms": {},
        # Reverse Learning state machine
        "rl_stage": "input",          # "input" | "questioning" | "report"
        "rl_gaps": [],
        "rl_questions": [],
        "rl_answers": [],
        "rl_question_index": 0,
        "rl_topic": "",
        # Quiz engine state
        "quiz_questions": [],
        "quiz_index": 0,
        "quiz_difficulty": "easy",
        "quiz_recent_results": [],
        "quiz_session_xp": 0,
        # Multiplayer state
        "mp_room_code": "",
        "mp_user_name": "",
        # Watsonx client singleton
        "_watsonx_client": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_watsonx_client():
    """
    Return (and lazily create) the shared WatsonxClient singleton.
    """
    from src.watsonx_client import WatsonxClient

    if st.session_state.get("_watsonx_client") is None:
        st.session_state["_watsonx_client"] = WatsonxClient()
    return st.session_state["_watsonx_client"]
