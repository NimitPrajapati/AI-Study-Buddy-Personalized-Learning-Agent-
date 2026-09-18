"""
app.py
Main Streamlit entry point for the AI Study Buddy application.
"""
import streamlit as st

from src.session_state import init_session

# --- Page configuration ---
st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

# --- Sidebar ---
st.sidebar.title("📚 AI Study Buddy")
st.sidebar.markdown("*Your Personalized Learning Agent*")
st.sidebar.markdown("---")

# Watsonx status indicator
from src.session_state import get_watsonx_client
client = get_watsonx_client()
if client.is_configured():
    st.sidebar.success("✅ watsonx connected")
else:
    st.sidebar.warning("⚠️ watsonx not configured — set WATSONX_API_KEY and WATSONX_PROJECT_ID in .env")

# User XP display
profile = st.session_state.profile
st.sidebar.markdown(f"**⭐ XP:** {profile.xp_points}")
st.sidebar.markdown(f"**🔥 Streak:** {profile.current_streak}")

docs = st.session_state.documents
if docs:
    st.sidebar.markdown(f"**📄 Documents:** {len(docs)} uploaded")
else:
    st.sidebar.markdown("**📄 Documents:** None uploaded yet")

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")
st.sidebar.markdown("""
- 📤 **Upload** — Upload notes/syllabus
- 💡 **Explain** — Persona-based explanations  
- 💬 **Chatbot** — Ask doubts with citations
- 🔄 **Reverse Learning** — Teach the AI
- 📖 **Story/Comic** — Chapter as a story
- 🧩 **Quiz** — Adaptive difficulty quiz
- 📊 **Weak Spots** — Performance analytics
- 📅 **Schedule** — Revision calendar
- 🕸️ **Mind Map** — Knowledge graph
- 🏆 **Multiplayer** — Live quiz with friends
- 🎯 **Exam Pattern** — Past paper analysis
- 🧑‍🎓 **Study Twin** — Topper's approach
- 🎤 **Voice Mode** — Voice-based doubts
""")

# --- Home page ---
st.title("📚 AI Study Buddy")
st.markdown("### Your Personalized AI Learning Agent powered by IBM watsonx Granite")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    #### 🚀 Getting Started
    1. **Upload** your notes or syllabus (PDF or TXT)
    2. **Choose a feature** from the sidebar pages
    3. **Start learning** with AI-powered assistance!
    """)

with col2:
    st.markdown("""
    #### ✨ Key Features
    - 🗣️ Persona-based explanations (Grandma, Cricket, etc.)
    - 💬 RAG Chatbot — answers only from your notes
    - 🧩 Adaptive quiz with difficulty scaling
    - 📊 Weak-spot prediction & spaced repetition
    """)

with col3:
    st.markdown("""
    #### 🎮 Advanced Features
    - 🔄 Reverse Learning (Feynman Technique)
    - 🕸️ Auto mind-map from your notes
    - 🏆 Multiplayer quiz with leaderboard
    - 🎤 Voice-based doubt solving
    """)

st.markdown("---")
if not docs:
    st.info("👆 Start by navigating to **Upload** in the sidebar to add your study material.")
else:
    st.success(f"✅ **{len(docs)} document(s)** loaded. Select any feature from the sidebar to begin!")
    for doc in docs:
        st.markdown(f"  - 📄 **{doc.file_name}** ({len(doc.chunks)} chunks)")
