import { httpDocuments, httpScoring } from './http'
import { mockApi } from './mock'
import type { ApiClient } from './types'

// Documents and scoring use FastAPI. Swap the other modules as their endpoints are designed.
export const api: ApiClient = { ...mockApi, documents: httpDocuments, scoring: httpScoring }
