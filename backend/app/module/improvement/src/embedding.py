from typing import List, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from improvement.src.data_loader import load_documents, data_path

# Embed using Bi-encoder
class EmbeddingPipeline:
    def __init__(self, model_name: str = "jinaai/jina-embeddings-v5-text-nano", chunk_size: int = 500, chunk_overlap: int = 75):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model = SentenceTransformer(
            model_name, 
            device='cpu', 
            trust_remote_code=True, 
            model_kwargs={"default_task": "text-matching"}
            )
        print(f"[INFO] Loaded embedding model: {model_name}")

    def chunk_documents(self, documents: List[Any]) -> List[Any]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(documents)

        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = f"CHUNK_{i:04d}"

        # Separate CV and JD chunks
        cv_chunks = [
            chunk for chunk in chunks
            if chunk.metadata.get("document_type") == "resume"
        ]

        jd_chunks = [
            chunk for chunk in chunks
            if chunk.metadata.get("document_type") == "job_description"
        ]

        print(f"[INFO] Split {len(documents)} documents into {len(chunks)} chunks.")
        print(f"[INFO] CV chunks: {len(cv_chunks)}")
        print(f"[INFO] JD chunks: {len(jd_chunks)}")
        return cv_chunks, jd_chunks

    def embed_chunks(self, cv_chunks, jd_chunks):

        cv_texts = [chunk.page_content for chunk in cv_chunks]
        jd_texts = [chunk.page_content for chunk in jd_chunks]
        if not cv_texts or not jd_texts:
            raise ValueError("CV and JD chunks must not be empty.")
        print(f"[INFO] Generating embeddings for {len(cv_texts)} CV chunks and {len(jd_texts)} JD chunks ...")


        cv_embeddings = self.model.encode(
            cv_texts, 
            task="retrieval",
            prompt_name="document",
            normalize_embeddings=True,
            convert_to_tensor=True,
            show_progress_bar=True
            )
        jd_embeddings = self.model.encode(
            jd_texts,
            task="retrieval",
            prompt_name="query",
            normalize_embeddings=True,
            convert_to_tensor=True,
            show_progress_bar=True
            )

        print(f"[INFO] CV Embeddings shape: {cv_embeddings.shape}")
        print(f"[INFO] JD Embeddings shape: {jd_embeddings.shape}")
        return cv_embeddings, jd_embeddings

if __name__ == "__main__":
    
    docs = load_documents(data_path)
    emb_pipe = EmbeddingPipeline()
    cv_chunks, jd_chunks = emb_pipe.chunk_documents(docs)
    cv_embeddings, jd_embeddings = emb_pipe.embed_chunks(cv_chunks, jd_chunks)