import { describe, expect, it } from 'vitest'
import { SAMPLES } from '../../lib/samples'
import { analyze, computeLineChanges } from './scoring'

describe('analyze', () => {
  // Expected values come from running the original data/job_assistant.html engine.
  it.each([
    [0, 73, [63, 100, 93, 51, 60], ['Tableau', 'Statistics', 'ETL', 'BigQuery', 'Snowflake', 'Data visualization']],
    [1, 60, [53, 71, null, 63, 60], ['Accessibility', 'Jest', 'Unit testing', 'CI/CD', 'Design systems', 'Figma', 'Agile']],
  ])('matches the prototype for sample %i', (index, overall, partScores, missing) => {
    const result = analyze(SAMPLES[index])
    expect(result.overall).toBe(overall)
    expect(result.parts.map(p => p.score)).toEqual(partScores)
    expect(result.missing).toEqual(missing)
  })

  it('falls back to frequent job terms when few known skills are found', () => {
    const jd = 'Gardener needed to prune roses, plant hedges, water lawns and tend orchards daily.'
    const result = analyze({ title: '', company: '', jd, cv: 'I prune roses.', cl: '' })
    expect(result.usedFallback).toBe(true)
    expect(result.matched).toContain('prune')
  })

  it('excludes a missing cover letter from the overall score', () => {
    const result = analyze({ ...SAMPLES[0], cl: '' })
    expect(result.parts.find(p => p.label === 'Cover letter alignment')?.score).toBeNull()
  })

  it('does not treat Java as matching JavaScript', () => {
    const result = analyze({ title: '', company: '', jd: 'Java, SQL and Python developer wanted.', cv: 'JavaScript, SQL, Python', cl: '' })
    expect(result.missing).toContain('Java')
  })
})

describe('computeLineChanges', () => {
  it('fixes spelling and wording on one line', () => {
    expect(computeLineChanges('- responsible for creating the managment report')[0]).toMatchObject({
      line: 0,
      after: '- Created the management report',
      type: 'Wording',
    })
  })

  it('keeps capitalisation of the word it replaces', () => {
    expect(computeLineChanges('Experiance in analytics')[0].after).toBe('Experience in analytics')
    expect(computeLineChanges('Worked on reports')[0].after).toBe('Delivered reports')
  })

  it('leaves clean lines alone', () => {
    expect(computeLineChanges('- Built 3 dashboards')).toEqual([])
  })
})
