from langchain_community.embeddings import HuggingFaceEmbeddings
from pinecone import Pinecone
from dotenv import load_dotenv
import os
load_dotenv()


embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")


# ── Pinecone RAG ──────────────────────────────────────────────────────────────
pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("mental-health-docs")

def get_relevant_info(query: str) -> str:
    vec     = embeddings.embed_query(query)
    results = index.query(top_k=3, vector=vec, include_metadata=True, include_values=False)
    return "".join(r["metadata"]["text"] for r in results["matches"])