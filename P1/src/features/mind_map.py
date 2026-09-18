"""
src/features/mind_map.py
Auto-generates a knowledge graph / mind-map from document chunks.
Uses networkx for graph structure and matplotlib for rendering.
"""
from __future__ import annotations

import io
import re
from typing import List, Optional, Tuple

from src.models import Chunk

_EXTRACT_PROMPT = """You are a knowledge graph extractor.
From the reference notes below, extract all concept relationships as triples.

Output ONLY lines in this format (one per line):
CONCEPT_A | relationship | CONCEPT_B

Rules:
- Use short concept names (1-4 words each).
- Relationship should be a short verb phrase (1-3 words), e.g. "is part of", "causes", "requires".
- Extract at least 10 triples if the notes are long enough.
- Do NOT include any other text, explanations, or headers.

Reference notes:
{context}
"""

_MAX_LABEL_LEN = 22


def extract_topic_relations(
    all_chunks: List[Chunk],
    watsonx_client,
    max_chunks: int = 8,
) -> List[Tuple[str, str, str]]:
    """
    Ask the LLM to extract (concept_A, relationship, concept_B) triples from the notes.

    Returns:
        List of (A, relationship, B) tuples.
    """
    context = "\n\n---\n\n".join(
        f"[{c.section_heading}]\n{c.content[:500]}"
        for c in all_chunks[:max_chunks]
    )

    prompt = _EXTRACT_PROMPT.format(context=context)
    raw = watsonx_client.generate_text(prompt, params={"max_new_tokens": 800})

    return _parse_triples(raw)


def build_graph(triples: List[Tuple[str, str, str]]):
    """
    Build a directed networkx graph from the triples.

    Returns:
        nx.DiGraph instance.
    """
    import networkx as nx

    G = nx.DiGraph()
    for a, rel, b in triples:
        a_label = a[:_MAX_LABEL_LEN]
        b_label = b[:_MAX_LABEL_LEN]
        G.add_edge(a_label, b_label, label=rel[:20])
    return G


def render_graph(G) -> bytes:
    """
    Render the graph as a PNG image and return the raw bytes.

    Returns:
        PNG image as bytes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    if len(G.nodes) == 0:
        # Return a placeholder image
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No relationships found", ha="center", va="center", fontsize=14)
        ax.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(14, 9))
        pos = nx.spring_layout(G, seed=42, k=2.5)

        nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#4A90D9",
                               node_size=1800, alpha=0.9)
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=8,
                                font_color="white", font_weight="bold")
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#555555",
                               arrows=True, arrowsize=20,
                               connectionstyle="arc3,rad=0.1")

        edge_labels = nx.get_edge_attributes(G, "label")
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                     ax=ax, font_size=7, font_color="#CC4400")

        ax.set_title("Knowledge Graph", fontsize=16, fontweight="bold", pad=20)
        ax.axis("off")
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _parse_triples(raw: str) -> List[Tuple[str, str, str]]:
    """Parse pipe-separated triples from LLM output."""
    triples: List[Tuple[str, str, str]] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and all(parts):
            triples.append((parts[0], parts[1], parts[2]))
    return triples
