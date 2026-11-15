# Shared LLM client

`mycareerai.core.llm.create_llm_client()` creates an OpenAI SDK client for OCR v2 and improvement. It loads `.env` without overriding existing environment variables and requires `OPENAI_API_KEY`. No client or network request is created at import time.

```python
from mycareerai.core.llm import create_llm_client

client = create_llm_client()
# Use client.responses.parse(...) or client.chat.completions.parse(...).
```

Defaults are a 120-second request timeout and two retries. Override them with `create_llm_client(timeout=30, max_retries=0)` if needed. Models, prompts, schemas and usage recording stay in the consuming modules. Improvement now uses the same explicit timeout as OCR v2.

To reuse one client across stages:

```python
from mycareerai.module.ocr_v2.extractor import extract_resume
from mycareerai.module.improvement.src.gap_analysis import EvidenceAssessor
from mycareerai.module.improvement.src.cv_improvement import CVRecommendationEngine

with create_llm_client() as client:
    document = extract_resume(pdf_path, document_id="CV_001", client=client)
    assessor = EvidenceAssessor(client=client)
    engine = CVRecommendationEngine(client=client)
    # Run assessment and improvement here, before the client closes.
```

All three consumers create a client through the factory when `client` is omitted. Tests can still inject a fake client without credentials or network access. Each factory call creates a new client; this is not a process-wide singleton.
