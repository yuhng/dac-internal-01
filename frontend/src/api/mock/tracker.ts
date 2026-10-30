import { STATUSES, type NewTrackerEntry, type Status, type TrackerEntry } from '../types'

const STORAGE_KEY = 'applyassist.tracker'

// Kept in memory as well so the tracker still works when storage is unavailable.
let memory: TrackerEntry[] | null = null

function isEntry(value: unknown): value is TrackerEntry {
  const entry = value as TrackerEntry | null
  return typeof entry?.id === 'string' && typeof entry.role === 'string' && STATUSES.includes(entry.status)
}

function load(): TrackerEntry[] {
  if (memory) return memory
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    memory = Array.isArray(stored) ? stored.filter(isEntry) : []
  } catch {
    memory = []
  }
  return memory
}

function save(entries: TrackerEntry[]) {
  memory = entries
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // Storage unavailable: keep in memory.
  }
}

export const trackerStore = {
  list: () => load(),
  add(entry: NewTrackerEntry) {
    const created: TrackerEntry = {
      ...entry,
      id: crypto.randomUUID(),
      status: 'Saved',
      date: new Date().toISOString().slice(0, 10),
    }
    save([created, ...load()])
    return created
  },
  updateStatus(id: string, status: Status) {
    save(load().map(e => (e.id === id ? { ...e, status } : e)))
  },
  remove(id: string) {
    save(load().filter(e => e.id !== id))
  },
}
