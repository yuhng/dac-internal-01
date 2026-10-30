import { mockApi } from './mock'
import type { ApiClient } from './types'

// Swap this for an HTTP implementation once the FastAPI endpoints are designed.
export const api: ApiClient = mockApi
