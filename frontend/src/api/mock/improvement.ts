import type { Analysis, Change } from '../types'
import { listJoin } from '../../lib/text'
import { computeLineChanges } from './scoring'

const SKILLS_NOTE = 'Only accept skills you genuinely have. Recruiters will ask about them.'

export function buildChanges(a: Analysis): Change[] {
  const lines = a.cv.split('\n')
  const lineChanges = computeLineChanges(a.cv)
  const changes: Change[] = lineChanges.map(({ line, ...c }, i) => ({
    ...c,
    id: `l${i}`,
    acceptedByDefault: true,
    edit: { kind: 'replaceLine', line, text: c.after },
  }))

  const summaryHead = lines.findIndex(l => /^\s*(summary|profile|professional summary|objective)\s*:?\s*$/i.test(l))
  if (summaryHead >= 0 && a.title) {
    const line = lines.findIndex((l, i) => i > summaryHead && l.trim())
    if (line >= 0) {
      const strengths = a.matched.slice(0, 2)
      const sentence = ` Seeking a ${a.title} role${a.company ? ` at ${a.company}` : ''}${strengths.length ? `, bringing hands-on ${listJoin(strengths)} experience` : ''}.`
      const base = lineChanges.find(c => c.line === line)?.after ?? lines[line]
      changes.push({
        id: 'sum',
        type: 'Alignment',
        labels: ['Tailor summary to the role'],
        before: base,
        after: base.trimEnd() + sentence,
        acceptedByDefault: true,
        edit: { kind: 'appendToLine', line, text: sentence },
      })
    }
  }

  const add = a.missing.slice(0, 5)
  if (add.length && !a.usedFallback) {
    const skillsHead = lines.findIndex(l => /^\s*(skills|technical skills|core skills)\b/i.test(l))
    if (skillsHead >= 0) {
      const line = /:\s*\S/.test(lines[skillsHead]) ? skillsHead : lines.findIndex((l, i) => i > skillsHead && l.trim())
      if (line >= 0) {
        const suffix = `, ${add.join(', ')}`
        changes.push({
          id: 'skills',
          type: 'Alignment',
          labels: ['Add missing job keywords'],
          note: SKILLS_NOTE,
          before: lines[line],
          after: lines[line].trimEnd() + suffix,
          acceptedByDefault: false,
          edit: { kind: 'appendToLine', line, text: suffix },
        })
      }
    } else {
      changes.push({
        id: 'skills',
        type: 'Alignment',
        labels: ['Add a Skills section with job keywords'],
        note: SKILLS_NOTE,
        before: '(no Skills section)',
        after: `SKILLS\n${add.join(', ')}`,
        acceptedByDefault: false,
        edit: { kind: 'appendLines', lines: ['', 'SKILLS', add.join(', ')] },
      })
    }
  }
  return changes
}
