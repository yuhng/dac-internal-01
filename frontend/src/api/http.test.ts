import { afterEach, expect, it, vi } from 'vitest'
import { httpScoring } from './http'

afterEach(() => vi.unstubAllGlobals())

const input = { title: '', company: '', jd: 'SQL', cv: 'SQL experience' }

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
