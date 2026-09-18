"""
pages/13_VoiceMode.py
Low-bandwidth voice-based doubt solving with STT and TTS fallback.
"""
import streamlit as st

from src.exceptions import OutOfScopeQueryError, STTFailureError, WatsonxAPIError
from src.features.chatbot import answer_doubt, format_citation
from src.features.voice_mode import synthesize_speech, transcribe_audio
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("🎤 Voice Mode")
st.markdown(
    "Ask doubts using your voice. If speech recognition fails, "
    "you can always type your question instead."
)

docs = st.session_state.documents
if not docs:
    st.info("📤 Please upload your study documents first (go to **Upload** page).")
    st.stop()

all_chunks = [chunk for doc in docs for chunk in doc.chunks]

st.markdown("---")

# --- Voice Input Section ---
st.subheader("🎙️ Step 1: Record or Upload Audio")

voice_mode = st.radio(
    "Input method:",
    ["Upload Audio File", "Type Question (Fallback)"],
    horizontal=True,
)

transcript = ""

if voice_mode == "Upload Audio File":
    audio_file = st.file_uploader(
        "Upload your question (WAV or MP3, max 60 sec)",
        type=["wav", "mp3"],
        help="Record your question on your phone and upload here.",
    )

    if audio_file is not None:
        st.audio(audio_file, format=f"audio/{audio_file.name.split('.')[-1]}")

        if st.button("🔊 Transcribe Audio"):
            with st.spinner("Transcribing..."):
                try:
                    audio_bytes = audio_file.read()
                    transcript = transcribe_audio(audio_bytes)
                    st.session_state["voice_transcript"] = transcript
                    st.success(f"✅ Transcribed: *{transcript}*")
                except STTFailureError as e:
                    st.error(f"❌ {e}")
                    st.info("💡 Switch to 'Type Question (Fallback)' to continue.")
                except Exception as e:
                    st.error(f"❌ Transcription error: {e}")

    transcript = st.session_state.get("voice_transcript", "")

else:
    # Typed fallback
    transcript = st.text_input(
        "✍️ Type your question:",
        placeholder="Ask anything from your uploaded notes...",
        max_chars=1000,
    )
    if transcript:
        st.session_state["voice_transcript"] = transcript

st.markdown("---")

# --- Review and Submit ---
st.subheader("📝 Step 2: Review & Ask")

display_transcript = st.session_state.get("voice_transcript", "")
editable_question = st.text_area(
    "Review / Edit your question before asking:",
    value=display_transcript,
    height=80,
)

if st.button("🔍 Get Answer", type="primary", disabled=not editable_question.strip()):
    question = editable_question.strip()

    if not question:
        st.warning("Please enter or transcribe a question first.")
    elif len(question) > 1000:
        st.error("❌ Question too long (max 1000 characters).")
    else:
        with st.spinner("Searching your notes..."):
            try:
                client = get_watsonx_client()
                answer, source_chunks = answer_doubt(
                    query=question,
                    all_chunks=all_chunks,
                    chat_history=[],
                    watsonx_client=client,
                )

                citation = format_citation(source_chunks)
                full_answer = answer
                if citation and citation not in answer:
                    full_answer = answer + f"\n\n{citation}"

                st.markdown("### 💬 Answer")
                st.markdown(full_answer)

                # --- TTS ---
                st.markdown("---")
                st.subheader("🔊 Step 3: Listen to Answer")
                with st.spinner("Generating audio..."):
                    try:
                        audio_bytes = synthesize_speech(answer)
                        st.audio(audio_bytes, format="audio/mp3")
                    except Exception as tts_err:
                        st.caption(f"ℹ️ Audio playback unavailable: {tts_err}")

                # Store in chat history
                st.session_state.chat_history.append({"role": "user", "content": question})
                st.session_state.chat_history.append({"role": "assistant", "content": full_answer})

            except OutOfScopeQueryError as e:
                st.warning(f"⚠️ {e}")
            except WatsonxAPIError as e:
                st.error(f"❌ watsonx API error: {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- Clear ---
if st.session_state.get("voice_transcript"):
    if st.button("🗑️ Clear"):
        st.session_state["voice_transcript"] = ""
        st.rerun()
