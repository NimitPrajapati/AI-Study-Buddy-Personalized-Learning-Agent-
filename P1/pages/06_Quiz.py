"""
pages/06_Quiz.py
Adaptive-difficulty quiz engine page.
"""
import streamlit as st

from src.exceptions import WatsonxAPIError
from src.features.quiz_engine import QuizEngine
from src.features.spaced_repetition import SpacedRepetitionScheduler
from src.features.weak_spot_analyzer import WeakSpotAnalyzer
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("🧩 Adaptive Quiz")
st.markdown(
    "Test your knowledge with AI-generated questions. "
    "Difficulty adjusts automatically based on your performance."
)

docs = st.session_state.documents
if not docs:
    st.info("📤 Please upload your study documents first (go to **Upload** page).")
    st.stop()

st.markdown("---")

engine = QuizEngine()
profile = st.session_state.profile

# --- Metrics bar ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("⭐ Total XP", profile.xp_points)
col2.metric("🔥 Streak", profile.current_streak)
col3.metric("📊 Difficulty", st.session_state.quiz_difficulty.capitalize())
col4.metric("📝 Answered", len(profile.quiz_history))

st.markdown("---")

# --- Setup panel (shown when no active quiz) ---
if not st.session_state.quiz_questions:
    st.subheader("⚙️ Quiz Setup")

    doc_names = ["All Documents"] + [d.file_name for d in docs]
    selected_scope = st.selectbox("📄 Source", doc_names)

    if selected_scope == "All Documents":
        all_chunks = [chunk for doc in docs for chunk in doc.chunks]
    else:
        sel_doc = next(d for d in docs if d.file_name == selected_scope)
        all_chunks = sel_doc.chunks

    topic = st.text_input("📌 Topic (leave blank for random from document)", "")
    n_questions = st.slider("Number of questions", min_value=3, max_value=10, value=5)

    if st.button("🚀 Generate Quiz", type="primary"):
        with st.spinner("Generating questions..."):
            try:
                client = get_watsonx_client()
                query = topic.strip() if topic.strip() else "general overview"
                questions = engine.generate_questions(
                    topic=query,
                    difficulty=st.session_state.quiz_difficulty,
                    all_chunks=all_chunks,
                    watsonx_client=client,
                    n=n_questions,
                )
                if not questions:
                    st.error("❌ Could not generate questions. Try a different topic or document.")
                else:
                    st.session_state.quiz_questions = questions
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_session_xp = 0
                    st.session_state.quiz_recent_results = []
                    st.rerun()
            except WatsonxAPIError as e:
                st.error(f"❌ watsonx API error: {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
else:
    # --- Active Quiz ---
    questions = st.session_state.quiz_questions
    idx = st.session_state.quiz_index

    if idx < len(questions):
        question = questions[idx]
        total = len(questions)

        st.subheader(f"Question {idx+1} of {total}")
        st.progress((idx) / total)

        difficulty_colors = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
        diff = question.get("difficulty", "easy")
        st.markdown(
            f"{difficulty_colors.get(diff, '⚪')} **Difficulty:** {diff.capitalize()} | "
            f"**Topic:** {question.get('topic', 'General')}"
        )

        st.markdown("---")
        st.markdown(f"### {question['question_text']}")

        options = question.get("options", [])
        if options:
            selected = st.radio("Select your answer:", options, key=f"q_{idx}")
        else:
            selected = st.text_input("Your answer:", key=f"q_{idx}")

        if st.button("✅ Submit Answer", type="primary"):
            is_correct = engine.evaluate_answer(question, selected[0] if selected else "")
            attempt = engine.record_attempt(profile, question, selected, is_correct)

            # Update difficulty
            st.session_state.quiz_recent_results.append(is_correct)
            new_difficulty = engine.adjust_difficulty(
                st.session_state.quiz_difficulty,
                st.session_state.quiz_recent_results,
            )
            st.session_state.quiz_difficulty = new_difficulty

            # Update weak spots and schedule
            analyzer = WeakSpotAnalyzer()
            analyzer.update_profile(profile)
            scheduler = SpacedRepetitionScheduler()
            scheduler.update_on_quiz_result(profile, question.get("topic", "General"), is_correct)

            xp_earned = profile.xp_points - (profile.xp_points - engine.award_xp(is_correct, profile.current_streak))
            st.session_state.quiz_session_xp += engine.award_xp(is_correct, profile.current_streak) if is_correct else 0

            if is_correct:
                st.success(f"✅ Correct! +{engine.award_xp(is_correct, profile.current_streak)} XP 🎉")
            else:
                st.error(f"❌ Incorrect. Correct answer: **{question.get('correct_answer')}**")
                # Show full correct option text
                for opt in options:
                    if opt.startswith(question.get("correct_answer", "")):
                        st.markdown(f"*Correct: {opt}*")
                        break

            st.session_state.quiz_index = idx + 1
            if st.session_state.quiz_index >= len(questions):
                st.session_state.quiz_stage_done = True
            st.rerun()

    else:
        # --- Quiz Complete ---
        st.balloons()
        st.success("🎉 Quiz Complete!")

        total = len(questions)
        correct_count = sum(
            1 for a in profile.quiz_history[-total:]
            if a.is_correct
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Correct", f"{correct_count}/{total}")
        col2.metric("⭐ XP Earned", st.session_state.quiz_session_xp)
        col3.metric("📊 Next Difficulty", st.session_state.quiz_difficulty.capitalize())

        if st.button("🔄 New Quiz", type="primary"):
            st.session_state.quiz_questions = []
            st.session_state.quiz_index = 0
            st.session_state.quiz_session_xp = 0
            if "quiz_stage_done" in st.session_state:
                del st.session_state["quiz_stage_done"]
            st.rerun()
