"""
pages/10_Multiplayer.py
Turn-based multiplayer quiz with leaderboard, streaks, and XP.
"""
import streamlit as st

from src.exceptions import (
    QuizNotStartedError,
    RoomFullError,
    RoomNotFoundError,
    WatsonxAPIError,
)
from src.features.multiplayer_quiz import MultiplayerQuizManager
from src.features.quiz_engine import QuizEngine
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("🏆 Multiplayer Live Quiz")
st.markdown(
    "Create a room, share the code with friends, and compete for the top spot on the leaderboard!"
)

docs = st.session_state.documents
manager = MultiplayerQuizManager()
engine = QuizEngine()
rooms = st.session_state.rooms
profile = st.session_state.profile

st.markdown("---")

tab_host, tab_join = st.tabs(["🎮 Host a Quiz", "🚪 Join a Quiz"])

# ===== HOST TAB =====
with tab_host:
    st.subheader("Create a New Quiz Room")

    if not docs:
        st.info("📤 Upload study documents first to generate questions.")
    else:
        host_name = st.text_input("Your display name:", value="Host", key="host_name")

        doc_names = ["All Documents"] + [d.file_name for d in docs]
        selected_scope = st.selectbox("📄 Source for questions:", doc_names, key="host_doc")

        if selected_scope == "All Documents":
            all_chunks = [chunk for doc in docs for chunk in doc.chunks]
        else:
            sel_doc = next(d for d in docs if d.file_name == selected_scope)
            all_chunks = sel_doc.chunks

        topic = st.text_input("📌 Topic (optional):", "", key="host_topic")
        n_q = st.slider("Number of questions:", 3, 10, 5, key="host_nq")

        if st.button("🚀 Create Room & Generate Questions", type="primary"):
            with st.spinner("Generating questions..."):
                try:
                    client = get_watsonx_client()
                    query = topic.strip() if topic.strip() else "general overview"
                    questions = engine.generate_questions(
                        topic=query,
                        difficulty="medium",
                        all_chunks=all_chunks,
                        watsonx_client=client,
                        n=n_q,
                    )
                    if not questions:
                        st.error("❌ Could not generate questions.")
                    else:
                        room = manager.create_room(
                            host_id=st.session_state.user_id,
                            host_name=host_name,
                            questions=questions,
                            rooms=rooms,
                        )
                        st.session_state.mp_room_code = room.room_code
                        st.session_state.mp_user_name = host_name
                        st.success(f"✅ Room created! Code: **{room.room_code}**")
                        st.info("Share this code with participants. Then click Start Quiz below.")
                        st.rerun()
                except WatsonxAPIError as e:
                    st.error(f"❌ watsonx API error: {e}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # Show existing hosted room
    hosted_code = st.session_state.mp_room_code
    if hosted_code and hosted_code in rooms:
        room = rooms[hosted_code]
        st.markdown("---")
        st.subheader(f"Room: **{hosted_code}**")
        st.markdown(f"**Status:** {room.status.capitalize()}")
        st.markdown(f"**Participants:** {len(room.participants)} / 10")
        st.markdown(f"**Questions:** {len(room.questions)}")

        if room.status == "waiting":
            if st.button("▶️ Start Quiz (need ≥2 players)", type="primary"):
                try:
                    manager.start_quiz(hosted_code, rooms)
                    st.success("Quiz started!")
                    st.rerun()
                except QuizNotStartedError as e:
                    st.warning(f"⚠️ {e}")

        if room.status == "active":
            st.success("✅ Quiz is live!")

        if room.status in ("active", "finished"):
            st.subheader("🏆 Leaderboard")
            leaderboard = manager.get_leaderboard(hosted_code, rooms)
            for rank, (uid, score) in enumerate(leaderboard, 1):
                medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."
                display = uid[:8] + "..."
                st.markdown(f"{medal} **{display}** — {score} pts")

        if st.button("🏁 End Room"):
            manager.finish_room(hosted_code, rooms)
            st.session_state.mp_room_code = ""
            st.rerun()

# ===== JOIN TAB =====
with tab_join:
    st.subheader("Join an Existing Quiz Room")

    join_name = st.text_input("Your display name:", value="Player", key="join_name")
    room_code_input = st.text_input("Room Code (6 characters):", max_chars=6, key="join_code").upper()

    if st.button("🚪 Join Room", type="primary"):
        if len(room_code_input) != 6 or not room_code_input.isalnum():
            st.warning("⚠️ Room code must be exactly 6 alphanumeric characters.")
        else:
            try:
                manager.join_room(room_code_input, st.session_state.user_id, rooms)
                st.session_state.mp_room_code = room_code_input
                st.session_state.mp_user_name = join_name
                st.success(f"✅ Joined room {room_code_input}!")
                st.rerun()
            except RoomNotFoundError as e:
                st.error(f"❌ {e}")
            except RoomFullError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    # Show active quiz for joined room
    active_code = st.session_state.mp_room_code
    if active_code and active_code in rooms:
        room = rooms[active_code]
        uid = st.session_state.user_id

        st.markdown("---")
        st.subheader(f"Room: **{active_code}**")
        st.markdown(f"**Status:** {room.status.capitalize()}")

        if room.status == "waiting":
            st.info("⏳ Waiting for the host to start the quiz...")

        elif room.status == "active":
            user_answers = room.answers.get(uid, [])
            q_idx = len(user_answers)  # Next question for this user

            if q_idx < len(room.questions):
                question = room.questions[q_idx]
                st.subheader(f"Question {q_idx + 1} of {len(room.questions)}")
                st.markdown(f"### {question['question_text']}")

                options = question.get("options", [])
                if options:
                    selected = st.radio("Select your answer:", options, key=f"mp_q_{q_idx}")
                else:
                    selected = st.text_input("Your answer:", key=f"mp_q_{q_idx}")

                if st.button("✅ Submit Answer", key=f"mp_submit_{q_idx}", type="primary"):
                    try:
                        xp, correct = manager.submit_answer(
                            active_code, uid, q_idx, selected[0] if selected else "", rooms
                        )
                        if correct:
                            st.success(f"✅ Correct! +{xp} XP")
                        else:
                            st.error(f"❌ Wrong. Correct: {question.get('correct_answer')}")
                        st.rerun()
                    except QuizNotStartedError as e:
                        st.warning(f"⚠️ {e}")
            else:
                st.success("✅ You've answered all questions!")

                # Show leaderboard
                st.subheader("🏆 Current Leaderboard")
                leaderboard = manager.get_leaderboard(active_code, rooms)
                for rank, (u, score) in enumerate(leaderboard, 1):
                    medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."
                    flag = " ← You" if u == uid else ""
                    st.markdown(f"{medal} **{u[:8]}...** — {score} pts{flag}")

        elif room.status == "finished":
            st.info("🏁 Quiz has ended.")
            st.subheader("🏆 Final Leaderboard")
            leaderboard = manager.get_leaderboard(active_code, rooms)
            for rank, (u, score) in enumerate(leaderboard, 1):
                medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."
                flag = " ← You" if u == uid else ""
                st.markdown(f"{medal} **{u[:8]}...** — {score} pts{flag}")

            if st.button("🚪 Leave Room"):
                st.session_state.mp_room_code = ""
                st.rerun()
