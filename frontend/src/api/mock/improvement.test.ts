import { describe, expect, it } from 'vitest'
import { applyChanges } from '../../lib/applyChanges'
import { SAMPLES } from '../../lib/samples'
import { buildChanges } from './improvement'
import { analyze } from './scoring'

const analysis = analyze(SAMPLES[0])
const changes = buildChanges(analysis)

describe('buildChanges', () => {
  it('leaves unverified skills unselected by default', () => {
    expect(changes.find(c => c.id === 'skills')?.acceptedByDefault).toBe(false)
  })

  it('adds a Skills section when the CV has none', () => {
    const cv = analysis.cv.replace(/SKILLS[\s\S]*$/, '').trim()
    const result = buildChanges(analyze({ ...SAMPLES[0], cv })).find(c => c.id === 'skills')
    expect(result?.edit.kind).toBe('appendLines')
  })
})

describe('applyChanges', () => {
  it('returns the CV unchanged when nothing is accepted', () => {
    expect(applyChanges(analysis.cv, [])).toBe(analysis.cv)
  })

  it('applies a summary fix and the tailored sentence to the same line', () => {
    const line = applyChanges(analysis.cv, changes).split('\n')[4]
    expect(line).toContain('2 years experience')
    expect(line).toContain('Seeking a Data Analyst role at Northwind Retail')
  })

  it('gives the same result regardless of change order', () => {
    expect(applyChanges(analysis.cv, [...changes].reverse())).toBe(applyChanges(analysis.cv, changes))
  })

  it('raises the score when all edits are applied', () => {
    const improved = analyze({ ...SAMPLES[0], cv: applyChanges(analysis.cv, changes) })
    expect(improved.overall).toBeGreaterThan(analysis.overall)
  })
})
