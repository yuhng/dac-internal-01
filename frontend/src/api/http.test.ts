import { afterEach, expect, it, vi } from 'vitest'
import { httpDocuments, httpScoring } from './http'

afterEach(() => vi.unstubAllGlobals())

const input = { title: '', company: '', jd: 'SQL', cv: 'SQL experience' }

it('uploads a PDF and uses the OCR v2 full text for scoring', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
    schema_version: '2', document_id: 'CV_001', document_version: 1,
    document_type: 'resume', text: 'SUMMARY\nPython analyst',
    metadata: { collection_method: 'gpt4o_pdf', review_status: 'pending' },
    sections: [], parsing_warnings: [],
  })))
  vi.stubGlobal('fetch', fetch)
  const file = new File(['%PDF-1.7'], 'cv.pdf', { type: 'application/pdf' })
  await expect(httpDocuments.extractText(file)).resolves.toBe('SUMMARY\nPython analyst')
  expect(fetch).toHaveBeenCalledWith('/api/documents/extract', { method: 'POST', body: expect.any(FormData) })
  expect(fetch.mock.calls[0][1].body.get('file')).toBe(file)
})

it('shows OCR v2 service errors to the uploader', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: 'The resume extraction service is unavailable. Try again in a moment.',
  }), { status: 503 })))
  await expect(httpDocuments.extractText(new File(['pdf'], 'cv.pdf'))).rejects.toThrow('extraction service is unavailable')
})

it('shows field validation errors instead of reporting an unreachable service', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: [
      { loc: ['body', 'jd'], msg: 'String should have at most 50000 characters' },
      { loc: ['body', 'cv'], msg: 'Field required' },
    ],
  }), { status: 422 })))
  await expect(httpScoring.analyze(input)).rejects.toThrow(
    'Job description: String should have at most 50000 characters\nCV: Field required',
  )
})

it('preserves the explanation for an unscorable job', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: 'No recognised skills were found in that job description.',
  }), { status: 422 })))
  await expect(httpScoring.analyze(input)).rejects.toThrow('No recognised skills')
})

it('handles an empty proxy error response', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 502 })))
  await expect(httpScoring.analyze(input)).rejects.toThrow('The scoring service could not be reached')
})
