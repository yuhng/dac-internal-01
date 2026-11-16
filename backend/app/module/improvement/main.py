import json
import logging
import os
from backend.app.core.llm.models import model_for
from pathlib import Path
from dotenv import load_dotenv
from improvement.src.data_loader import load_documents, data_path
from improvement.src.embedding import EmbeddingPipeline
from improvement.src.vector_store import ChromaDBPipeline
from improvement.src.reranker import RerankingPipeline
from improvement.src.gap_analysis import EvidenceAssessor, GapAnalysisPipeline
from improvement.src.cv_improvement import CVImprovementPipeline, CVRecommendationEngine

# Run from the repo root: python -m improvement.main
OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "reranked_results.json"
GAP_OUTPUT_PATH = OUTPUT_PATH.with_name("gap_analysis.json")
CV_OUTPUT_PATH = OUTPUT_PATH.with_name("cv_improvements.json")
model_name = os.getenv("LLM_MODEL")  # optional override for both stages; else models.yaml

def main(model_name,top_k: int = 20, top_n: int = 10):

    # 1. Load Documents
    docs = load_documents(data_path)

    # 2. Chunk and generate embeddings
    emb_pipe = EmbeddingPipeline()
    cv_chunks, jd_chunks = emb_pipe.chunk_documents(docs)
    cv_embeddings, jd_embeddings = emb_pipe.embed_chunks(cv_chunks, jd_chunks)

    # 3. ChromaDB ingestion and retrieval
    vector_db = ChromaDBPipeline()
    vector_db.ingest(cv_chunks, cv_embeddings)  # upsert, safe to re-run
    retrieved = vector_db.retrieve(jd_chunks, jd_embeddings, top_k=top_k)

    # 4. Cross-encoder reranking
    reranker = RerankingPipeline(top_n=top_n)
    reranked_results = []
    for result in retrieved:
        reranked = reranker.rerank(jd_text=result['jd_text'], retrieved_chunks=result['cv_evidence'])
        reranked_results.append({
            "jd_chunk_id": result["jd_chunk_id"],
            "jd_text": result["jd_text"],
            "cv_evidence": reranked
        })
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(reranked_results, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"[INFO] Saved {len(reranked_results)} JD chunks to {OUTPUT_PATH}")

    # 6. LLM gap analysis
    assessor = EvidenceAssessor(model_name=model_name or model_for("gap_analysis"))
    gap_results = GapAnalysisPipeline(assessor=assessor).analyze(reranked_results)
    GAP_OUTPUT_PATH.write_text(json.dumps(gap_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[INFO] Saved {len(gap_results)} gap assessments to {GAP_OUTPUT_PATH}")

    # 7. CV improvement recommendations
    engine = CVRecommendationEngine(model_name=model_name or model_for("cv_improvement"))
    cv_results = CVImprovementPipeline(engine).generate(gap_results, cv_chunks)
    CV_OUTPUT_PATH.write_text(json.dumps(cv_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[INFO] Saved {len(cv_results)} CV improvement results to {CV_OUTPUT_PATH}")
    return cv_results

if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
    main(model_name=model_name)
