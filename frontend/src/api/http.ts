import { mockApi } from './mock'
import { ApiError } from './types'

const UNREACHABLE = 'The document service could not be reached. Try again, or paste the text instead.'

/** PDFs go to the Document API. Plain text is read in the browser and needs no server. */
async function extractText(file: File) {
  if (!/\.pdf$/i.test(file.name)) return mockApi.documents.extractText(file)

  const body = new FormData()
  body.append('file', file)

  let response: Response
  try {
    response = await fetch('/api/documents/extract', { method: 'POST', body })
  } catch {
    throw new ApiError(UNREACHABLE)
  }

  // The dev proxy answers with an empty 502 when the backend is down, so the body may not be JSON.
  const result: { text?: string; detail?: unknown } | null = await response.json().catch(() => null)
  if (response.ok && result?.text) return result.text
  throw new ApiError(typeof result?.detail === 'string' ? result.detail : UNREACHABLE)
}

export const httpDocuments = { extractText }
