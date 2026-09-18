"""
pages/05_StoryComic.py
Converts chapter/topic into a short story or comic-panel script.
"""
import streamlit as st

from src.exceptions import WatsonxAPIError
from src.features.story_generator import generate_story
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("📖 Story & Comic Generator")
st.markdown(
    "Transform a chapter or concept from your notes into an engaging story or comic script!"
)

docs = st.session_state.documents
if not docs:
    st.info("📤 Please upload your study documents first (go to **Upload** page).")
    st.stop()

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    doc_names = [d.file_name for d in docs]
    selected_doc_name = st.selectbox("📄 Select Document", doc_names)
    selected_doc = next(d for d in docs if d.file_name == selected_doc_name)

    topic = st.text_input(
        "📌 Chapter / Topic to Narrate",
        placeholder="e.g., Chapter 3: Cell Division, The French Revolution...",
        max_chars=200,
    )

with col2:
    style = st.radio(
        "🎨 Output Format",
        options=["story", "comic"],
        format_func=lambda x: "📖 Short Story" if x == "story" else "🎭 Comic Script",
        help="Story: narrative prose. Comic: numbered panel format.",
    )

    st.markdown("---")
    st.info(
        "**Story:** A short narrative under 400 words.\n\n"
        "**Comic:** 5-8 numbered panels with dialogue."
    )

st.markdown("---")

if st.button("🎬 Generate", type="primary", disabled=not topic.strip()):
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        with st.spinner(f"Writing your {style}..."):
            try:
                client = get_watsonx_client()
                result = generate_story(
                    topic=topic.strip(),
                    style=style,
                    all_chunks=selected_doc.chunks,
                    watsonx_client=client,
                )

                icon = "📖" if style == "story" else "🎭"
                st.markdown(f"## {icon} Your {style.title()}")
                st.markdown(result)

            except WatsonxAPIError as e:
                st.error(f"❌ watsonx API error: {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
