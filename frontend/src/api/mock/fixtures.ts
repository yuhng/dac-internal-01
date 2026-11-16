import { SAMPLES } from '../../lib/samples'
import type { Analysis } from '../types'

/** A fixed analysis of the first sample for the chat and improvement mock tests. */
export const sampleAnalysis = (cv = SAMPLES[0].cv): Analysis => ({
  ...SAMPLES[0],
  cv,
  id: 'test-analysis',
  overall: 66,
  band: 'good',
  bandLabel: 'Good match',
  parts: [
    { label: 'Skills coverage', weight: 40, score: 56, detail: '5 of 9 required skills found' },
    { label: 'Experience relevance', weight: 60, score: 73, detail: 'How closely your work and project experience matches the role' },
  ],
  matched: ['SQL', 'Python', 'Excel'],
  missing: ['Tableau', 'Statistics'],
  recommendations: [
    { severity: 'high', text: 'Add evidence of **Tableau** to your experience or skills, if you have it.' },
    { severity: 'med', text: 'Add evidence of **Statistics** to your experience or skills, if you have it.' },
  ],
  requirements: [],
  confidence: { level: 'high', reasons: [] },
  cap: null,
  engineVersion: 'scoring-v2',
  methodology: [],
})
