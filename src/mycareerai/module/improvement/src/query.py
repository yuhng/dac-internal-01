from langchain_core.documents import Document
from improvement.src.embedding import EmbeddingPipeline
from improvement.src.vector_store import ChromaDBPipeline

emb_pipe = EmbeddingPipeline()
vector_db = ChromaDBPipeline() 

query = "Experience building ETL pipelines with PySpark on Databricks"
query_embedding = emb_pipe.model.encode(
    [query], task="retrieval", prompt_name="query",
    normalize_embeddings=True, convert_to_tensor=True,
)

results = vector_db.retrieve([Document(page_content=query)], query_embedding, top_k=5)
for r in results[0]["cv_evidence"]:  # single query -> single result
    metadata = r["metadata"]
    print(f"{r['bi_encoder_score']:.3f}  {metadata['section_name']}  {metadata.get('job_title', '')}")

# lookups without a query embedding
print("Total chunks:", vector_db.collection.count())
projects = vector_db.collection.get(where={"section_name": "projects"})
print("Project chunks:", projects["ids"])
