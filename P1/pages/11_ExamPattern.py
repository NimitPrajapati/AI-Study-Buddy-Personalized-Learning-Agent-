"""
pages/11_ExamPattern.py
Exam pattern predictor based on uploaded past papers.
"""
import streamlit as st

from src.exceptions import WatsonxAPIError
from src.features.exam_pattern import analyze_papers
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("🎯 Exam Pattern Predictor")
st.markdown(
    "Upload past exam papers and get AI-powered predictions about "
    "likely topics and question types for your next exam."
)

st.markdown("---")

exam_papers = st.session_state.exam_papers

if not exam_papers:
    st.info(
        "📝 No exam papers uploaded yet.\n\n"
        "Go to the **Upload** page and upload past exam papers "
        "in the 'Past Exam Papers' section."
    )
    st.stop()

st.success(f"✅ {len(exam_papers)} exam paper(s) loaded.")
if len(exam_papers) < 2:
    st.warning(
        "⚠️ For more reliable predictions, upload at least 2-3 past papers. "
        f"Currently: {len(exam_papers)} paper(s)."
    )

st.markdown("---")

# Show loaded papers
with st.expander("📄 Loaded Papers"):
    for paper in exam_papers:
        st.markdown(f"- **{paper.file_name}** ({len(paper.chunks)} sections)")

if st.button("🔍 Analyze Exam Patterns", type="primary"):
    paper_chunks_list = [paper.chunks for paper in exam_papers]

    with st.spinner("Analyzing past papers..."):
        try:
            client = get_watsonx_client()
            result = analyze_papers(
                paper_chunks_list=paper_chunks_list,
                watsonx_client=client,
            )

            if result.get("warning"):
                st.warning(f"⚠️ {result['warning']}")

            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📌 Most Tested Topics")
                topics = result.get("topics", [])
                if topics:
                    for i, topic in enumerate(topics, 1):
                        st.markdown(f"{i}. {topic}")
                else:
                    st.info("No specific topics identified.")

            with col2:
                st.subheader("📝 Question Types Found")
                qtypes = result.get("question_types", [])
                if qtypes:
                    for qt in qtypes:
                        st.markdown(f"- {qt}")
                else:
                    st.info("No specific question types identified.")

            patterns = result.get("patterns", [])
            if patterns:
                st.markdown("---")
                st.subheader("🔍 Observed Patterns")
                for pattern in patterns:
                    st.markdown(f"- {pattern}")

        except WatsonxAPIError as e:
            st.error(f"❌ watsonx API error: {e}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
