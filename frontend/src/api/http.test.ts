import { afterEach, expect, it, vi } from 'vitest'
import { httpDocuments, httpScoring, type ScoringV2Response } from './http'

afterEach(() => vi.unstubAllGlobals())

const document = {
  schema_version: '2', document_id: 'CV_001', document_version: 1,
  document_type: 'resume', text: 'SUMMARY\nPython analyst',
  metadata: { collection_method: 'claude_pdf', review_status: 'pending' },
  sections: [], parsing_warnings: [],
}
const input = { title: 'Analyst', company: 'Acme', jd: 'SQL and Python', cv: document.text, document }

const v2 = (overall: Partial<ScoringV2Response['overall']> = {}): ScoringV2Response => ({
  skill_scores: {
    skills: [
      { jd_name: 'Python', importance: 'required', matched: true, matches: [{ original_text: 'Skills: Python' }] },
      { jd_name: 'SQL', importance: 'required', matched: false, matches: [] },
      { jd_name: 'Docker', importance: 'preferred', matched: false, matches: [] },
    ],
    coverage: {
      required: { matched: 1, requested: 2 }, preferred: { matched: 0, requested: 1 }, unspecified: { matched: 0, requested: 0 },
    },
  },
  relevance_scores: { jev_confidence: 0.8 },
  overall: {
    skill_score_100: 35.29, relevance_score_100: 75, overall_score_100: 59.12,
    method: 'weighted_skills_and_relevance', provisional: false, ...overall,
  },
})

const respond = (body: unknown, status = 200) => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fetch)
  return fetch
}

it('uploads a PDF and keeps both its text and the structured document', async () => {
  const fetch = respond(document)
  const file = new File(['%PDF-1.7'], 'cv.pdf', { type: 'application/pdf' })
  await expect(httpDocuments.extract(file)).resolves.toEqual({ text: document.text, document })
  expect(fetch).toHaveBeenCalledWith('/api/documents/extract', { method: 'POST', body: expect.any(FormData) })
  expect(fetch.mock.calls[0][1].body.get('file')).toBe(file)
})

it('rejects non-PDF uploads without calling the backend', async () => {
  const fetch = respond(document)
  await expect(httpDocuments.extract(new File(['cv'], 'cv.txt'))).rejects.toThrow('Upload your CV as a PDF')
  expect(fetch).not.toHaveBeenCalled()
})

it('shows OCR v2 service errors to the uploader', async () => {
  respond({ detail: 'The resume extraction service is unavailable. Try again in a moment.' }, 503)
  await expect(httpDocuments.extract(new File(['pdf'], 'cv.pdf'))).rejects.toThrow('extraction service is unavailable')
})

it('needs an uploaded PDF before scoring', async () => {
  const fetch = respond(v2())
  await expect(httpScoring.analyze({ ...input, document: null })).rejects.toThrow('Upload your CV as a PDF')
  expect(fetch).not.toHaveBeenCalled()
})

it('sends the structured document and maps the v2 score into an analysis', async () => {
  const fetch = respond(v2())
  const analysis = await httpScoring.analyze(input)
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ title: 'Analyst', company: 'Acme', jd: 'SQL and Python', document })
  expect(analysis.overall).toBe(59)
  expect(analysis.band).toBe('fair')
  expect(analysis.parts.map(p => [p.label, p.weight, p.score])).toEqual([['Skills coverage', 40, 35], ['Experience relevance', 60, 75]])
  expect(analysis.matched).toEqual(['Python'])
  expect(analysis.missing).toEqual(['SQL', 'Docker'])
  expect(analysis.requirements[0]).toMatchObject({ text: 'Python', importance: 'must', tier: 'listed', evidence: 'Skills: Python' })
  expect(analysis.recommendations.map(r => r.severity)).toEqual(['high', 'med'])
  expect(analysis.confidence.level).toBe('high')
  expect(analysis.quality).toBeUndefined()
  expect(analysis.cv).toBe(document.text)
})

it('explains a relevance-only score and flags it', async () => {
  respond(v2({ method: 'relevance_only', skill_score_100: null, overall_score_100: 75, provisional: true }))
  const analysis = await httpScoring.analyze(input)
  expect(analysis.parts.map(p => [p.label, p.weight])).toEqual([['Experience relevance', 100]])
  expect(analysis.confidence.level).toBe('medium')
  expect(analysis.confidence.reasons[0]).toContain('based on experience only')
})

it('reports a missing relevance score instead of showing a number', async () => {
  respond(v2({ relevance_score_100: null, overall_score_100: null, method: null }))
  await expect(httpScoring.analyze(input)).rejects.toThrow('no score was produced')
})

it('shows field validation errors instead of reporting an unreachable service', async () => {
  respond({
    detail: [
      { loc: ['body', 'jd'], msg: 'String should have at most 50000 characters' },
      { loc: ['body', 'document', 'sections', 0, 'section_name'], msg: 'Input should be a valid section name' },
    ],
  }, 422)
  await expect(httpScoring.analyze(input)).rejects.toThrow(
    'Job description: String should have at most 50000 characters\nCV: Input should be a valid section name',
  )
})

it('preserves the explanation for an unscorable job', async () => {
  respond({ detail: 'No skills extracted and no explanation supplied' }, 422)
  await expect(httpScoring.analyze(input)).rejects.toThrow('No skills extracted')
})

it('handles an empty proxy error response', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 502 })))
  await expect(httpScoring.analyze(input)).rejects.toThrow('The scoring service could not be reached')
})
