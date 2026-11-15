# ApplyAssist frontend

React, TypeScript, Tailwind CSS and TanStack Query, ported from the prototype in `data/job_assistant.html`.

```sh
npm install
npm run dev     # local dev server
npm test        # unit tests
npm run lint
npm run build
```

## Structure

- `src/pages`: one component per view (Overview, Score, Improve CV, Assistant, Tracker)
- `src/api/types.ts`: the `ApiClient` contract, grouped by the backend modules in the architecture reference
- `src/api/client.ts`: selects the implementation the app uses
- `src/api/http.ts`: the parts of the contract served by FastAPI
- `src/api/mock`: the prototype's heuristics. Nothing here calls a server or an AI model
- `src/state`: session state shared across pages

## Connecting the backend

Pages only talk to `api` from `src/api/client.ts`. PDF uploads call FastAPI through `src/api/http.ts`. Start the
backend from the repo root with `uv run uvicorn mycareerai.main:app --reload`; `npm run dev` proxies `/api` to it.

PDF uploads use `ocr_v2` (GPT-4o), requiring `OPENAI_API_KEY` and the `PG*` database settings in the backend environment. The full v2 response is stored in `documents.row` as JSONB; the UI uses its `text` for editing and scoring. The legacy OCR extraction and legacy `resumes` projection are not used for uploads. Each upload gets a new document ID.

Scoring also uses FastAPI. Other modules still use the mock, because those endpoints are not designed yet. Remove the demo-mode copy in
`Layout`, `OverviewPage`, `ResultPanel`, `ImprovePage` and `ChatPage` when the mock goes away.

Authentication is not built, because the identity provider and session model are still open decisions.
