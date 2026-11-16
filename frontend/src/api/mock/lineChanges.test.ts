import { describe, expect, it } from 'vitest'
import { computeLineChanges } from './lineChanges'

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
