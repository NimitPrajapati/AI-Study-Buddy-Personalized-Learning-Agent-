"""
pages/09_MindMap.py
Auto-generated knowledge graph / mind-map from uploaded notes.
"""
import streamlit as st

from src.exceptions import WatsonxAPIError
from src.features.mind_map import build_graph, extract_topic_relations, render_graph
from src.session_state import get_watsonx_client, init_session

init_session()

st.title("🕸️ Mind Map / Knowledge Graph")
st.markdown(
    "Automatically generate a visual knowledge graph from your notes. "
    "Shows how concepts relate to each other."
)

docs = st.session_state.documents
if not docs:
    st.info("📤 Please upload your study documents first (go to **Upload** page).")
    st.stop()

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    doc_names = ["All Documents"] + [d.file_name for d in docs]
    selected_scope = st.selectbox("📄 Generate from:", doc_names)

with col2:
    max_chunks = st.slider("Depth (chunks to analyse)", min_value=3, max_value=12, value=8)

if selected_scope == "All Documents":
    all_chunks = [chunk for doc in docs for chunk in doc.chunks]
else:
    sel_doc = next(d for d in docs if d.file_name == selected_scope)
    all_chunks = sel_doc.chunks

st.markdown("---")

if st.button("🗺️ Generate Mind Map", type="primary"):
    with st.spinner("Extracting concept relationships..."):
        try:
            client = get_watsonx_client()
            triples = extract_topic_relations(
                all_chunks=all_chunks,
                watsonx_client=client,
                max_chunks=max_chunks,
            )

            if len(triples) < 3:
                st.warning(
                    "⚠️ Only a few relationships were found. "
                    "The document may be too short, or try uploading more content."
                )

            G = build_graph(triples)

            if len(G.nodes) < 3:
                st.warning("Not enough concepts found to build a meaningful map.")
            else:
                with st.spinner("Rendering graph..."):
                    img_bytes = render_graph(G)
                    st.image(img_bytes, caption=f"Knowledge Graph — {len(G.nodes)} concepts, {len(G.edges)} relationships", use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Extracted Relationships")
                for a, rel, b in triples[:30]:
                    st.markdown(f"- **{a}** *{rel}* **{b}**")
                if len(triples) > 30:
                    st.caption(f"...and {len(triples) - 30} more relationships.")

        except WatsonxAPIError as e:
            st.error(f"❌ watsonx API error: {e}")
        except ImportError as e:
            st.error(f"❌ Missing library: {e}. Install networkx and matplotlib.")
        except Exception as e:
            st.error(f"❌ Error generating mind map: {e}")
