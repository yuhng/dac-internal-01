import type { Change } from '../types'
import { SPELLING, WEAK_PHRASES } from './data'

/** Keeps a replacement capitalised when it replaces a capitalised word. */
const matchCase = (source: string, replacement: string) =>
  /^[A-Z]/.test(source) ? replacement[0].toUpperCase() + replacement.slice(1) : replacement

export interface LineChange extends Pick<Change, 'before' | 'after' | 'labels'> {
  line: number
  type: 'Grammar' | 'Wording'
}

export function computeLineChanges(text: string): LineChange[] {
  const changes: LineChange[] = []
  text.split('\n').forEach((before, line) => {
    let current = before
    let type: LineChange['type'] = 'Grammar'
    const labels = new Set<string>()
    const step = (re: RegExp, replacer: (...args: string[]) => string, label: string, kind?: LineChange['type']) => {
      const next = current.replace(re, replacer)
      if (next !== current) {
        current = next
        labels.add(label)
        if (kind) type = kind
      }
    }
    step(/(^|\s)i(?=[\s'’])/g, (_, space) => `${space}I`, 'Capitalise “I”')
    step(/(\S) {2,}(?=\S)/g, (_, char) => `${char} `, 'Remove extra spaces')
    for (const [bad, good] of Object.entries(SPELLING)) {
      step(new RegExp(`\\b${bad}\\b`, 'gi'), m => matchCase(m, good), `Spelling: ${good}`)
    }
    for (const [re, replacer, label] of WEAK_PHRASES) {
      step(re, (m, verb) => matchCase(m, replacer(m, verb)), label, 'Wording')
    }
    step(/^(\s*[-•*]\s*)([a-z])/, (_, prefix, char) => prefix + char.toUpperCase(), 'Capitalise bullet')
    if (current !== before) changes.push({ line, before, after: current, labels: [...labels], type })
  })
  return changes
}
