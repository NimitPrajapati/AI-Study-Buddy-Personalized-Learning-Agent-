"""
pages/08_Schedule.py
Spaced-repetition revision schedule page.
"""
import streamlit as st

from src.features.spaced_repetition import SpacedRepetitionScheduler
from src.session_state import init_session

init_session()

st.title("📅 Revision Schedule")
st.markdown(
    "Your personalized spaced-repetition schedule, "
    "automatically generated from your weak spots."
)

st.markdown("---")

profile = st.session_state.profile
scheduler = SpacedRepetitionScheduler()

# --- Regenerate if weak topics changed ---
if profile.weak_topics and not profile.revision_schedule:
    profile.revision_schedule = scheduler.compute_schedule(profile.weak_topics)

schedule = profile.revision_schedule

if not schedule:
    if not profile.quiz_history:
        st.info(
            "📝 No schedule generated yet. Complete some quizzes first to identify "
            "weak topics, then a revision schedule will be created automatically.\n\n"
            "Go to **Quiz** to get started!"
        )
    else:
        st.info(
            "🟢 No weak topics identified yet! Keep taking quizzes to generate a schedule."
        )
    st.stop()

# --- Today's topics ---
todays_topics = scheduler.get_todays_topics(profile)
if todays_topics:
    st.subheader("📌 Today's Revision Topics")
    for topic in todays_topics:
        st.markdown(f"  ✅ **{topic}**")
    st.markdown("---")

# --- Schedule table ---
st.subheader("🗓️ Full Revision Plan")
rows = scheduler.format_schedule_for_display(schedule)

if rows:
    import pandas as pd
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Schedule is empty.")

st.markdown("---")

# --- Manual regenerate ---
if profile.weak_topics:
    st.subheader("🔄 Weak Topics Being Scheduled")
    for t in profile.weak_topics:
        st.markdown(f"- {t}")

    if st.button("♻️ Regenerate Schedule from Today"):
        profile.revision_schedule = scheduler.compute_schedule(profile.weak_topics)
        st.success("✅ Schedule regenerated!")
        st.rerun()
