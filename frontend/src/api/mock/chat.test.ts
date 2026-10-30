import { describe, expect, it } from 'vitest'
import { SAMPLES } from '../../lib/samples'
import { reply } from './chat'
import { analyze } from './scoring'

const analysis = analyze(SAMPLES[0])
const flatten = (message: string, a = analysis as typeof analysis | null) => JSON.stringify(reply(message, a))

describe('reply', () => {
  it('asks for an analysis before answering job-specific questions', () => {
    expect(flatten('Explain my score', null)).toContain('Run a score')
  })

  it.each([
    ['Explain my score', '73/100'],
    ['Which keywords am I missing?', 'Tableau'],
    ['How can I improve my CV?', 'Top actions'],
    ['Draft a cover letter opening', 'Northwind Retail'],
    ['Give me interview questions', 'STAR'],
    ['tell me about the weather', 'scripted demo'],
  ])('routes %j', (message, expected) => {
    expect(flatten(message)).toContain(expected)
  })
})
