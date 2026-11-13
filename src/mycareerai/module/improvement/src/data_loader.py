import json
from pathlib import Path
from langchain_core.documents import Document


data_path = '/Users/yuhngtan/sandbox/improvement/data'

def load_documents(data_path: str):
    documents = []

    for json_file in Path(data_path).glob("**/*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            doc_meta = {
                "source": str(json_file),
                "document_id": data.get("document_id"),
                "document_type": data.get("document_type"),
                **data.get("metadata", {}),  # candidate_id, job_title, company, ...
            }

            for section in data.get("sections", []):
                section_meta = {"section_id": section.get("section_id"), "section_name": section.get("section_name")}
                
                # a section has either its own "content" or a list of "entries" (jobs, projects), each with "content"
                for item in section.get("entries", [section]):
                    extra = {k: v for k, v in item.items() if k not in ("content", "section_id", "section_name")}
                    documents.append(Document(
                        page_content=item["content"],
                        metadata={**doc_meta, **section_meta, **extra},
                    ))

        except Exception as e:
            print(f"[ERROR] {json_file}: {e}")

    return documents


if __name__ == "__main__":
    docs = load_documents(data_path)

    cv_docs = [doc for doc in docs if doc.metadata["document_type"] == "resume"]
    jd_docs = [doc for doc in docs if doc.metadata["document_type"] == "job_description"]

    print(f"Loaded {len(docs)} documents ({len(cv_docs)} CV, {len(jd_docs)} JD).")
    print("Example document:", docs[0] if docs else None)
