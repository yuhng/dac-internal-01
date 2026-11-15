import torch

class RetrievalPipeline:
    def __init__(self, top_k=5):
        self.top_k = top_k

    def retrieve(self, cv_chunks, jd_chunks, cv_embeddings, jd_embeddings):
        # normalized embeddings → dot product = cosine similarity; shape (n_jd, n_cv)
        similarity_matrix = jd_embeddings @ cv_embeddings.T

        top_k = min(self.top_k, len(cv_chunks))  # torch.topk errors if k > n_cv
        top_scores, top_indices = torch.topk(similarity_matrix, k=top_k, dim=1)  # sorted best first

        results = []
        for jd_idx, jd_chunk in enumerate(jd_chunks):
            for score, cv_idx in zip(top_scores[jd_idx].tolist(), top_indices[jd_idx].tolist()):
                results.append({
                    "jd_chunk": jd_chunk,
                    "cv_chunk": cv_chunks[cv_idx],
                    "bi_encoder_score": score,
                })
        return results

if __name__ == "__main__":
    from improvement.src.data_loader import load_documents, data_path
    from improvement.src.embedding import EmbeddingPipeline
    from improvement.src.vector_store import ChromaDBPipeline

    emb_pipe = EmbeddingPipeline()
    cv_chunks, jd_chunks = emb_pipe.chunk_documents(load_documents(data_path))
    cv_embeddings, jd_embeddings = emb_pipe.embed_chunks(cv_chunks, jd_chunks)

    vector_db = ChromaDBPipeline()
    vector_db.ingest(cv_chunks, cv_embeddings)
    results = vector_db.retrieve(jd_chunks, jd_embeddings, top_k=3)
    for r in results:
        jd_meta, cv_meta = r["jd_chunk"].page_content, r["cv_chunk"].page_content
        print(f"{r['bi_encoder_score']:.3f}  {jd_meta} -> {cv_meta}")
