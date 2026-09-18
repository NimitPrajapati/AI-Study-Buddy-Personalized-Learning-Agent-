"""
pages/04_ReverseLearning.py
Feynman Technique — student explains a concept and AI finds knowledge gaps.
"""
import streamlit as st

from src.exceptions import InsufficientExplanationError, WatsonxAPIError
from src.features.reverse_learning import (
    evaluate_explanation,
    generate_gap_report,
)
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("🔄 Reverse Learning (Feynman Technique)")
st.markdown(
    "**Explain a concept in your own words** — the AI will find gaps in your understanding "
    "and ask targeted questions to help you truly master the material."
)

docs = st.session_state.documents
if not docs:
    st.info("📤 Please upload your study documents first (go to **Upload** page).")
    st.stop()

st.markdown("---")

all_chunks = [chunk for doc in docs for chunk in doc.chunks]

# --- Stage: Input ---
if st.session_state.rl_stage == "input":
    st.subheader("Step 1: Explain the Concept")

    topic = st.text_input(
        "📌 Topic you want to explain",
        placeholder="e.g., Photosynthesis, Newton's First Law...",
        value=st.session_state.rl_topic,
    )
    student_text = st.text_area(
        "✍️ Your Explanation (minimum 30 words)",
        height=200,
        placeholder="Explain the concept in your own words, as if teaching a friend...",
    )

    word_count = len(student_text.split()) if student_text else 0
    st.caption(f"Word count: {word_count} / 30 minimum")

    if st.button("🚀 Submit Explanation", type="primary"):
        if not topic.strip():
            st.warning("Please enter a topic.")
        elif not student_text.strip():
            st.warning("Please write your explanation.")
        else:
            with st.spinner("Analyzing your explanation..."):
                try:
                    client = get_watsonx_client()
                    result = evaluate_explanation(
                        student_text=student_text.strip(),
                        topic=topic.strip(),
                        all_chunks=all_chunks,
                        watsonx_client=client,
                    )

                    if result["verbatim_warning"]:
                        st.warning(
                            "⚠️ Your explanation looks very similar to the notes. "
                            "Please try explaining in your own words!"
                        )
                        st.stop()

                    st.session_state.rl_topic = topic.strip()
                    st.session_state.rl_gaps = result["gaps"]
                    st.session_state.rl_questions = result["questions"]
                    st.session_state.rl_answers = []
                    st.session_state.rl_question_index = 0
                    st.session_state["rl_student_text"] = student_text.strip()
                    st.session_state.rl_stage = "questioning"
                    st.rerun()

                except InsufficientExplanationError as e:
                    st.warning(f"⚠️ {e}")
                except WatsonxAPIError as e:
                    st.error(f"❌ watsonx API error: {e}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# --- Stage: Questioning ---
elif st.session_state.rl_stage == "questioning":
    questions = st.session_state.rl_questions
    idx = st.session_state.rl_question_index
    answers = st.session_state.rl_answers

    st.subheader(f"Step 2: Answer Follow-up Questions — {idx+1} / {len(questions)}")
    st.info(f"**Topic:** {st.session_state.rl_topic}")

    if st.session_state.rl_gaps:
        with st.expander("🔍 Identified Knowledge Gaps"):
            for gap in st.session_state.rl_gaps:
                st.markdown(f"- {gap}")

    if idx < len(questions):
        st.markdown(f"### ❓ Question {idx+1}")
        st.markdown(f"**{questions[idx]}**")

        answer_key = f"rl_answer_{idx}"
        user_answer = st.text_area("Your answer:", key=answer_key, height=120)

        if st.button("➡️ Submit Answer", type="primary"):
            if not user_answer.strip():
                st.warning("Please write an answer before continuing.")
            else:
                answers.append(user_answer.strip())
                st.session_state.rl_answers = answers
                st.session_state.rl_question_index = idx + 1

                if st.session_state.rl_question_index >= len(questions):
                    st.session_state.rl_stage = "report"
                st.rerun()
    else:
        st.session_state.rl_stage = "report"
        st.rerun()

# --- Stage: Report ---
elif st.session_state.rl_stage == "report":
    st.subheader("Step 3: Knowledge Gap Report")
    st.success("✅ Analysis complete! Here is your personalized feedback:")

    with st.spinner("Generating your gap report..."):
        try:
            # Generate report only once
            if "rl_report" not in st.session_state:
                client = get_watsonx_client()
                report = generate_gap_report(
                    topic=st.session_state.rl_topic,
                    student_explanation=st.session_state.get("rl_student_text", ""),
                    gaps=st.session_state.rl_gaps,
                    questions=st.session_state.rl_questions,
                    student_answers=st.session_state.rl_answers,
                    all_chunks=all_chunks,
                    watsonx_client=client,
                )
                st.session_state["rl_report"] = report

            st.markdown(st.session_state["rl_report"])

        except WatsonxAPIError as e:
            st.error(f"❌ watsonx API error: {e}")
        except Exception as e:
            st.error(f"❌ Error generating report: {e}")

    st.markdown("---")
    if st.button("🔄 Start New Session", type="secondary"):
        for key in ["rl_stage", "rl_gaps", "rl_questions", "rl_answers",
                    "rl_question_index", "rl_topic", "rl_student_text", "rl_report"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.rl_stage = "input"
        st.session_state.rl_topic = ""
        st.rerun()
