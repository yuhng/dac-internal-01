import type { Change, ChangeEdit } from '../api/types'

const ORDER: Record<ChangeEdit['kind'], number> = { replaceLine: 0, appendToLine: 1, appendLines: 2 }

/** Applies edits to the CV. Whole-line replacements go first so appends land on the edited line. */
export function applyChanges(cv: string, changes: Change[]): string {
  const lines = cv.split('\n')
  const ordered = [...changes].sort((a, b) => ORDER[a.edit.kind] - ORDER[b.edit.kind])
  for (const { edit } of ordered) {
    if (edit.kind === 'replaceLine') lines[edit.line] = edit.text
    else if (edit.kind === 'appendToLine') lines[edit.line] = lines[edit.line].trimEnd() + edit.text
    else lines.push(...edit.lines)
  }
  return lines.join('\n')
}
