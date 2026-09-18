"""
pages/12_StudyTwin.py
Study Twin feature — simulates a topper's approach to mastering a topic.
"""
import streamlit as st

from src.exceptions import WatsonxAPIError
from src.features.study_twin import generate_study_twin
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("🧑‍🎓 Study Twin")
st.markdown(
    "Meet **Alex** — your AI Study Twin who always scores 100%. "
    "See exactly how a topper would approach and master any topic from your notes."
)

docs = st.session_state.documents
if not docs:
    st.info("📤 Please upload your study documents first (go to **Upload** page).")
    st.stop()

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    doc_names = ["All Documents"] + [d.file_name for d in docs]
    selected_scope = st.selectbox("📄 Source Notes", doc_names)

    if selected_scope == "All Documents":
        all_chunks = [chunk for doc in docs for chunk in doc.chunks]
    else:
        sel_doc = next(d for d in docs if d.file_name == selected_scope)
        all_chunks = sel_doc.chunks

    topic = st.text_input(
        "📌 Topic to Master",
        placeholder="e.g., Photosynthesis, Trigonometry, Indian Independence Movement...",
        max_chars=200,
    )

with col2:
    st.markdown("#### 🎓 About Alex")
    st.info(
        "**Study Twin Alex:**\n"
        "- Always scores 100%\n"
        "- Gives topic-specific tips\n"
        "- Shares memory tricks\n"
        "- Predicts exam questions\n"
        "- Provides revision checklist"
    )

st.markdown("---")

if st.button("🤝 Get Alex's Study Plan", type="primary", disabled=not topic.strip()):
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        with st.spinner(f"Alex is preparing the study plan for '{topic}'..."):
            try:
                client = get_watsonx_client()
                response = generate_study_twin(
                    topic=topic.strip(),
                    all_chunks=all_chunks,
                    watsonx_client=client,
                )

                st.markdown(response)

                st.markdown("---")
                st.caption(
                    "⚠️ *Study Twin is an AI persona based on your notes. "
                    "Always verify information with your teacher or textbook.*"
                )

            except WatsonxAPIError as e:
                st.error(f"❌ watsonx API error: {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
