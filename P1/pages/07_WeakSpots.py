"""
pages/07_WeakSpots.py
Weak-spot prediction report based on quiz performance.
"""
import streamlit as st

from src.features.weak_spot_analyzer import WeakSpotAnalyzer
from src.session_state import init_session

init_session()

st.title("📊 Weak-Spot Prediction Report")
st.markdown(
    "See which topics you're struggling with, based on your quiz performance. "
    "Topics below 60% accuracy are flagged as weak."
)

st.markdown("---")

profile = st.session_state.profile
quiz_history = profile.quiz_history

if not quiz_history:
    st.info(
        "📝 No quiz history yet. Complete at least one quiz to see your weak-spot report.\n\n"
        "Go to **Quiz** to get started!"
    )
    st.stop()

analyzer = WeakSpotAnalyzer()
accuracy_map = analyzer.analyze(quiz_history)

if not accuracy_map:
    st.info(
        "📝 Not enough data yet. Each topic needs at least **3 quiz attempts** "
        "for a reliable accuracy score.\n\nKeep quizzing!"
    )

    # Show raw stats even without reliable accuracy
    from collections import Counter
    topic_counts = Counter(a.topic for a in quiz_history)
    st.subheader("Attempted Topics So Far")
    for topic, count in topic_counts.most_common():
        st.markdown(f"- **{topic}**: {count} attempt(s)")
    st.stop()

# --- Metrics ---
weak_topics = analyzer.get_weak_topics(accuracy_map)
total_topics = len(accuracy_map)
weak_count = len(weak_topics)

col1, col2, col3 = st.columns(3)
col1.metric("📚 Topics Tested", total_topics)
col2.metric("🔴 Weak Topics", weak_count)
col3.metric("🟢 Strong Topics", total_topics - weak_count)

st.markdown("---")

# --- Bar chart ---
st.subheader("📈 Topic Accuracy Chart")

topics = list(accuracy_map.keys())
accuracies = [accuracy_map[t] * 100 for t in topics]

chart_data = {"Topic": topics, "Accuracy (%)": accuracies}

import pandas as pd
df = pd.DataFrame(chart_data).sort_values("Accuracy (%)")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(10, max(4, len(topics) * 0.5)))
    colors = ["#e74c3c" if a < 60 else "#2ecc71" for a in df["Accuracy (%)"]]
    bars = ax.barh(df["Topic"], df["Accuracy (%)"], color=colors, edgecolor="white")
    ax.axvline(x=60, color="#e67e22", linestyle="--", linewidth=2, label="60% threshold")
    ax.set_xlabel("Accuracy (%)", fontsize=12)
    ax.set_xlim(0, 105)
    ax.set_title("Topic Accuracy (Red = Weak)", fontsize=14, fontweight="bold")

    for bar, acc in zip(bars, df["Accuracy (%)"]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{acc:.0f}%", va="center", fontsize=10)

    red_patch = mpatches.Patch(color="#e74c3c", label="Weak (<60%)")
    green_patch = mpatches.Patch(color="#2ecc71", label="Strong (≥60%)")
    ax.legend(handles=[red_patch, green_patch, ax.lines[0]], loc="lower right")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
except Exception:
    st.bar_chart(df.set_index("Topic"))

st.markdown("---")

# --- Detailed Table ---
st.subheader("📋 Detailed Report")
report_rows = analyzer.generate_report(accuracy_map)
df_report = pd.DataFrame(report_rows)
st.dataframe(df_report, use_container_width=True, hide_index=True)

# --- Weak topics highlight ---
if weak_topics:
    st.markdown("---")
    st.subheader("🔴 Focus Areas (Weak Topics)")
    for topic in weak_topics:
        acc = accuracy_map[topic]
        st.markdown(
            f"- **{topic}** — {acc*100:.0f}% accuracy "
            f"({'Critical — below 40%!' if acc < 0.4 else 'Needs improvement'})"
        )

    st.info(
        "💡 **Tip:** Check your **Schedule** page for a spaced-repetition revision plan "
        "targeting these weak topics."
    )
else:
    st.success("🎉 Great work! All tested topics are above the 60% threshold.")
