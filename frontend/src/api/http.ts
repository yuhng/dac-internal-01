import { mockApi } from './mock'
import { ApiError, type Analysis, type ScoreInput } from './types'

const UNREACHABLE = 'The document service could not be reached. Try again, or paste the text instead.'
const SCORING_UNREACHABLE = 'The scoring service could not be reached. Try again in a moment.'

/** PDFs use OCR v2 via the Document API; scoring consumes its full text. */
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

async function analyze(input: ScoreInput) {
  let response: Response
  try {
    response = await fetch('/api/scoring/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
  } catch {
    throw new ApiError(SCORING_UNREACHABLE)
  }

  const result: (Analysis & { detail?: unknown }) | null = await response.json().catch(() => null)
  if (response.ok && result) return result
  if (response.status === 422 && Array.isArray(result?.detail)) {
    const labels: Record<string, string> = { title: 'Job title', company: 'Company', jd: 'Job description', cv: 'CV' }
    const messages = result.detail.flatMap(issue => {
      if (!issue || typeof issue.msg !== 'string') return []
      const field = Array.isArray(issue.loc) ? issue.loc[1] : undefined
      return [`${labels[field] ?? 'Request'}: ${issue.msg}`]
    })
    throw new ApiError(messages.join('\n') || 'Check your job description and CV, then try again.')
  }
  throw new ApiError(typeof result?.detail === 'string' ? result.detail : SCORING_UNREACHABLE)
}

export const httpDocuments = { extractText }
export const httpScoring = { analyze }
