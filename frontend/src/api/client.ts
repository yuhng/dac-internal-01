import { httpDocuments } from './http'
import { mockApi } from './mock'
import type { ApiClient } from './types'

// Documents use FastAPI. Swap the other modules as their endpoints are designed.
export const api: ApiClient = { ...mockApi, documents: httpDocuments }
