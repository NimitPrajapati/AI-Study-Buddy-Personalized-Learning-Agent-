"""
pages/01_Upload.py
Document upload and management page.
"""
import streamlit as st

from src.document_ingestion import upload_and_parse
from src.exceptions import (
    ChunkingFailureError,
    DuplicateDocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from src.persistence import save_document_metadata
from src.session_state import init_session

init_session()

st.title("📤 Upload Study Material")
st.markdown("Upload your notes, syllabus, or past exam papers (PDF or TXT, max 10 MB each).")

st.markdown("---")

# --- Upload Section ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📚 Study Notes / Syllabus")
    uploaded_files = st.file_uploader(
        "Upload your notes",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="notes_uploader",
        help="Upload PDF or TXT files containing your study material.",
    )

    if uploaded_files:
        existing_hashes = [doc.content_hash for doc in st.session_state.documents]
        for uploaded_file in uploaded_files:
            try:
                doc = upload_and_parse(
                    file_name=uploaded_file.name,
                    file_bytes=uploaded_file.read(),
                    existing_hashes=existing_hashes,
                )
                st.session_state.documents.append(doc)
                existing_hashes.append(doc.content_hash)
                st.success(
                    f"✅ **{doc.file_name}** uploaded — "
                    f"{len(doc.chunks)} chunks extracted."
                )
            except DuplicateDocumentError as e:
                st.warning(f"⚠️ {e}")
            except (UnsupportedFileTypeError, FileTooLargeError, EmptyDocumentError, ChunkingFailureError) as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error processing '{uploaded_file.name}': {e}")

        # Persist metadata
        meta = [
            {
                "file_name": d.file_name,
                "file_type": d.file_type,
                "chunks": len(d.chunks),
                "upload_timestamp": d.upload_timestamp.isoformat(),
            }
            for d in st.session_state.documents
        ]
        save_document_metadata(meta)

with col2:
    st.subheader("📝 Past Exam Papers")
    exam_files = st.file_uploader(
        "Upload past exam papers",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="exam_uploader",
        help="Used for exam pattern prediction.",
    )

    if exam_files:
        existing_exam_hashes = [doc.content_hash for doc in st.session_state.exam_papers]
        for uploaded_file in exam_files:
            try:
                doc = upload_and_parse(
                    file_name=uploaded_file.name,
                    file_bytes=uploaded_file.read(),
                    existing_hashes=existing_exam_hashes,
                )
                st.session_state.exam_papers.append(doc)
                existing_exam_hashes.append(doc.content_hash)
                st.success(
                    f"✅ **{doc.file_name}** uploaded as exam paper — "
                    f"{len(doc.chunks)} chunks."
                )
            except DuplicateDocumentError as e:
                st.warning(f"⚠️ {e}")
            except (UnsupportedFileTypeError, FileTooLargeError, EmptyDocumentError) as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

st.markdown("---")

# --- Current documents ---
docs = st.session_state.documents
exam_papers = st.session_state.exam_papers

if docs:
    st.subheader(f"📄 Loaded Study Documents ({len(docs)})")
    for doc in docs:
        with st.expander(f"📄 {doc.file_name} — {len(doc.chunks)} chunks"):
            st.markdown(f"- **Type:** {doc.file_type.upper()}")
            st.markdown(f"- **Uploaded:** {doc.upload_timestamp.strftime('%Y-%m-%d %H:%M')}")
            st.markdown(f"- **Chunks:** {len(doc.chunks)}")
            st.markdown("**Sample chunk headings:**")
            headings = list({c.section_heading for c in doc.chunks})[:5]
            for h in headings:
                st.markdown(f"  - {h}")

    if st.button("🗑️ Clear All Study Documents", type="secondary"):
        st.session_state.documents = []
        st.session_state.chat_history = []
        st.rerun()
else:
    st.info("No study documents uploaded yet. Use the uploader above.")

if exam_papers:
    st.subheader(f"📝 Loaded Exam Papers ({len(exam_papers)})")
    for doc in exam_papers:
        st.markdown(f"- 📝 **{doc.file_name}** ({len(doc.chunks)} chunks)")

    if st.button("🗑️ Clear All Exam Papers", type="secondary"):
        st.session_state.exam_papers = []
        st.rerun()
