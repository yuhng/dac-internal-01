import { describe, expect, it } from 'vitest'
import { SAMPLES } from '../../lib/samples'
import { analyze, computeLineChanges } from './scoring'

describe('analyze', () => {
  it.each([
    [0, 66, [56, 100, 51, 60], ['Tableau', 'Statistics', 'A/B testing', 'ETL', 'BigQuery', 'Snowflake', 'Data visualization']],
    [1, 60, [53, 71, 63, 60], ['Accessibility', 'Jest', 'Unit testing', 'CI/CD', 'Design systems', 'Figma', 'Agile']],
  ])('scores sample %i', (index, overall, partScores, missing) => {
    const result = analyze(SAMPLES[index])
    expect(result.overall).toBe(overall)
    expect(result.parts.map(p => p.score)).toEqual(partScores)
    expect(result.missing).toEqual(missing)
  })

  it('falls back to frequent job terms when few known skills are found', () => {
    const jd = 'Gardener needed to prune roses, plant hedges, water lawns and tend orchards daily.'
    const result = analyze({ title: '', company: '', jd, cv: 'I prune roses.' })
    expect(result.usedFallback).toBe(true)
    expect(result.matched).toContain('prune')
  })

  it('does not treat Java as matching JavaScript', () => {
    const result = analyze({ title: '', company: '', jd: 'Java, SQL and Python developer wanted.', cv: 'JavaScript, SQL, Python' })
    expect(result.missing).toContain('Java')
  })

  it('scores skills from the CV only', () => {
    const result = analyze({
      title: '',
      company: '',
      jd: 'Python, SQL, and Tableau skills are required for this analytics position.',
      cv: 'Python and SQL experience',
    })
    expect(result.matched).toEqual(['SQL', 'Python'])
    expect(result.parts.map(part => part.weight)).toEqual([47, 24, 18, 11])
    expect(result.parts.every(part => part.score !== null)).toBe(true)
    expect(result.recommendations.some(rec => /cover letter/i.test(rec.text))).toBe(false)
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
