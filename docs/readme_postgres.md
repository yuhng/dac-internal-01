# Postgres ingestion

How an uploaded resume gets from the frontend into the Postgres database running in Docker.

Code: `src/mycareerai/core/postgre/ingest.py`, `src/mycareerai/api/documents.py`  
Tests: `tests/core/postgre/`

## Flow

```
Browser (drop a PDF on the Overview page)
  │  POST /api/documents/extract   (multipart form, field "file")
  ▼
Vite dev server :5173  ── proxies /api ──►  FastAPI :8000
  │
  ▼
api/documents.py  extract()
  1. Rejects anything that is not a .pdf (415) or is over 10 MB (413)
  2. Writes the file to a temp folder and runs the OCR module → one record matching data/schema.json
  3. Saves the record to Postgres
  4. Returns the record as JSON to the browser
  │
  ▼
core/postgre/ingest.py
  │  psycopg connects to 127.0.0.1:5433 (settings come from the PG* variables)
  ▼
Docker container "db" (postgres:18), port 5432 inside the container
  tables: documents, resumes
```

1. **Frontend**: `frontend/src/api/http.ts` `extractText()` sends PDFs to `/api/documents/extract`. Plain-text files never leave the browser, so they are not stored.
2. **Proxy**: `frontend/vite.config.ts` forwards `/api` to `http://127.0.0.1:8000`, where the backend runs.
3. **API**: `src/mycareerai/api/documents.py` validates the upload, calls `build_record()` from the OCR module (see `docs/readme_ocr.md`), then calls the save function in `ingest.py`.
4. **Database**: `ingest.py` opens one connection and, in a single transaction:
   - creates both tables if they don't exist yet (so no migration step is needed)
   - upserts the whole record into `documents`
   - upserts the resume fields into `resumes`

   Both rows commit together, or neither does.

## Tables

| Table | Key | Holds |
|-------|-----|-------|
| `documents` | `id` | The full record as `jsonb` in the `row` column, plus `created_at` |
| `resumes` | `document_id` → `documents.id` | The resume fields as columns (`email`, `skills`, `hard_skills`, `occupation`, `industry`, …) so they can be filtered and joined. `work_experience` and `education` are `jsonb`, the skill lists are `text[]` |

Uploading the same file again replaces its rows instead of adding duplicates, because both inserts are `ON CONFLICT ... DO UPDATE`.
Deleting a `documents` row also deletes its `resumes` row (`ON DELETE CASCADE`).

## Configuration

`.env` in the repo root holds the settings for both sides:

```sh
POSTGRES_PASSWORD=...        # used by docker-compose to create the database user
PGHOST=127.0.0.1
PGPORT=5433                  # docker-compose maps host 5433 → container 5432
PGUSER=dac
PGDATABASE=mycareerai_dev
PGPASSWORD=${POSTGRES_PASSWORD}
```

`src/mycareerai/main.py` loads `.env` at startup with `load_dotenv()`, and `psycopg.connect()` reads the `PG*` variables from there. Variables that are already set (for example in a deployment) take priority over `.env`.

## Running it

Run these commands from the repo root.

Start the database:

```sh
docker compose up -d db
```

Start the backend:

```sh
uv run uvicorn mycareerai.main:app --reload
```

Start the frontend:

```sh
cd frontend && npm run dev
```

Then drop a PDF on the Overview page.

## Checking the data

```sh
# list the tables
docker compose exec db psql -U dac -d mycareerai_dev -c '\dt'

# latest uploads
docker compose exec db psql -U dac -d mycareerai_dev -c 'select document_id, occupation, skills from resumes order by created_at desc limit 5'
```

`src/mycareerai/core/postgre/query.py` shows how to read rows from Python.

## Errors

| What the user sees | Cause |
|--------------------|-------|
| 415 "Only PDF files can be read." | The file is not a `.pdf` |
| 413 "That file is larger than 10 MB." | The upload is too big |
| 422 | OCR failed, or the record did not match `data/schema.json` |
| 503 "The resume could not be saved…" | Postgres is unreachable or the insert failed. The full error is in the backend log |

The data volume `postgres_data` keeps the data when the container is stopped. `docker compose down -v` deletes it.
