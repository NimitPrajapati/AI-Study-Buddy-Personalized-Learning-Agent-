"""
pages/02_Explain.py
Persona-based "Explain Like I'm..." page.
"""
import streamlit as st

from src.exceptions import WatsonxAPIError
from src.features.explanation import explain_topic
from src.session_state import get_watsonx_client, init_session
from src.validation import ALLOWED_PERSONAS

init_session()

st.title("💡 Explain Like I'm...")
st.markdown("Get any topic from your notes explained in a style you love.")

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
        "📌 Topic or Concept to Explain",
        placeholder="e.g., Photosynthesis, Newton's Laws, World War II causes...",
        max_chars=200,
    )

with col2:
    persona = st.selectbox(
        "🎭 Explanation Style",
        ALLOWED_PERSONAS,
        help="Choose how you want the concept explained.",
    )
    st.markdown(f"**Selected:** {persona}")

st.markdown("---")

if st.button("✨ Generate Explanation", type="primary", disabled=not topic.strip()):
    if not topic.strip():
        st.warning("Please enter a topic to explain.")
    else:
        with st.spinner(f"Explaining '{topic}' as '{persona}'..."):
            try:
                client = get_watsonx_client()
                result = explain_topic(
                    topic=topic.strip(),
                    persona=persona,
                    chunks=selected_doc.chunks,
                    watsonx_client=client,
                )
                st.markdown("### 📖 Explanation")
                st.markdown(result)

                # Show which sections were used
                from src.document_ingestion import retrieve_relevant_chunks
                relevant = retrieve_relevant_chunks(topic, selected_doc.chunks, top_k=3)
                if relevant:
                    with st.expander("📍 Source Sections Used"):
                        for chunk in relevant:
                            st.markdown(
                                f"- **Page {chunk.page_number}** | {chunk.section_heading}"
                            )

            except WatsonxAPIError as e:
                st.error(f"❌ watsonx API error: {e}")
            except ValueError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
