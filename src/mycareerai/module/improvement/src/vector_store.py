from typing import List
import chromadb
from langchain_core.documents import Document

CHROMA_PATH = "/Users/yuhngtan/sandbox/improvement/chroma_db"


class ChromaDBPipeline:
    def __init__(self, persist_directory=CHROMA_PATH, collection_name="cv_embeddings"):
        self.client = chromadb.PersistentClient(path=persist_directory)

        # cosine space: distance = 1 - cosine similarity
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        print(f"[INFO] ChromaDB initialized: {collection_name}")

    def ingest(self, chunks: List[Document], embeddings):
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings must align.")
        if not chunks:
            return

        self.collection.upsert(
            ids=[f"{c.metadata['document_id']}:{c.metadata['chunk_id']}" for c in chunks],
            documents=[c.page_content for c in chunks],
            embeddings=embeddings.tolist(),
            # Chroma only accepts str/int/float/bool metadata values
            metadatas=[{k: v for k, v in c.metadata.items() if isinstance(v, (str, int, float, bool))} for c in chunks],
        )
        print(f"[INFO] Ingested {len(chunks)} CV chunks")

    def retrieve(self, jd_chunks: List[Document], jd_embeddings, top_k: int = 5, where: dict | None = None):
        # one query per JD chunk, all sent in a single call
        res = self.collection.query(
            query_embeddings=jd_embeddings.tolist(),
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # one result per JD chunk, with its CV hits grouped under "cv_evidence"
        results = []
        for jd_chunk, texts, metas, dists in zip(jd_chunks, res["documents"], res["metadatas"], res["distances"]):
            results.append({
                "jd_chunk_id": jd_chunk.metadata.get("chunk_id"),
                "jd_text": jd_chunk.page_content,
                "cv_evidence": [
                    {"text": text, "metadata": meta, "bi_encoder_score": 1 - dist}  # higher is better
                    for text, meta, dist in zip(texts, metas, dists)
                ],
            })
        return results
