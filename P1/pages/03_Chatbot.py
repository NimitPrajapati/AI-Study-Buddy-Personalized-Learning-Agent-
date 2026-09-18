"""
pages/03_Chatbot.py
RAG-based doubt-solving chatbot with mandatory source citations.
"""
import streamlit as st

from src.exceptions import OutOfScopeQueryError, WatsonxAPIError
from src.features.chatbot import answer_doubt, format_citation
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("💬 Doubt-Solving Chatbot")
st.markdown(
    "Ask any question about your uploaded notes. "
    "The chatbot answers **only from your material** and always cites the source."
)

docs = st.session_state.documents
if not docs:
    st.info("📤 Please upload your study documents first (go to **Upload** page).")
    st.stop()

st.markdown("---")

# Document selector (for multi-doc use)
doc_names = ["All Documents"] + [d.file_name for d in docs]
selected_scope = st.selectbox("📄 Answer from:", doc_names)

# Collect all relevant chunks
if selected_scope == "All Documents":
    all_chunks = [chunk for doc in docs for chunk in doc.chunks]
else:
    selected_doc = next(d for d in docs if d.file_name == selected_scope)
    all_chunks = selected_doc.chunks

st.markdown("---")

# --- Chat History Display ---
chat_history = st.session_state.chat_history

for message in chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Input ---
if prompt := st.chat_input("Ask a doubt about your notes..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Validate
    if len(prompt) > 1000:
        st.error("❌ Question too long. Please keep it under 1000 characters.")
        st.stop()

    # Store user message
    chat_history.append({"role": "user", "content": prompt})

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching your notes..."):
            try:
                client = get_watsonx_client()
                answer, source_chunks = answer_doubt(
                    query=prompt,
                    all_chunks=all_chunks,
                    chat_history=chat_history[:-1],  # Exclude current user message
                    watsonx_client=client,
                )

                citation = format_citation(source_chunks)
                full_response = answer
                if citation and citation not in answer:
                    full_response = answer + f"\n\n{citation}"

                st.markdown(full_response)
                chat_history.append({"role": "assistant", "content": full_response})

            except OutOfScopeQueryError as e:
                warning_msg = f"⚠️ {e}"
                st.warning(warning_msg)
                chat_history.append({"role": "assistant", "content": warning_msg})

            except WatsonxAPIError as e:
                error_msg = f"❌ watsonx API error: {e}"
                st.error(error_msg)

            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")

# Clear chat button
if chat_history:
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
