from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
from backend.app.core.llm.models import model_for


class RerankingPipeline:
    # bge-reranker-v2-m3 is a pointwise cross-encoder: scores each (JD, CV) pair independently, 0-1 via sigmoid
    def __init__(self, model_name: str = model_for("reranker"), top_n: int = 3, batch_size: int = 8):
        self.model = CrossEncoder(model_name, device="cpu")
        self.top_n = top_n
        self.batch_size = batch_size
        print(f"[INFO] Loaded reranker : {model_name}")

    def rerank(self, jd_text: str, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not retrieved_chunks:
            return []

        scores = self.model.predict(
            [(jd_text, chunk["text"]) for chunk in retrieved_chunks],
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        results = sorted(
            ({**chunk, "cross_encoder_score": float(score)} for chunk, score in zip(retrieved_chunks, scores)),
            key=lambda x: x["cross_encoder_score"],
            reverse=True,
        )[:self.top_n]

        for rank, result in enumerate(results, start=1):
            result["rank"] = rank
        return results
