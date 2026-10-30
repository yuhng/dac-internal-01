/** Contract between the UI and the backend modules in the architecture reference. */

export interface ScoreInput {
  title: string
  company: string
  jd: string
  cv: string
  cl: string
}

export type Band = 'strong' | 'good' | 'fair' | 'weak'
export type Severity = 'high' | 'med' | 'low'

export interface ScorePart {
  label: string
  weight: number
  /** null when the part does not apply, e.g. no cover letter was provided. */
  score: number | null
  detail: string
}

export interface Recommendation {
  severity: Severity
  /** Inline rich text, see RichText. */
  text: string
}

export interface Analysis extends ScoreInput {
  id: string
  overall: number
  band: Band
  bandLabel: string
  parts: ScorePart[]
  matched: string[]
  missing: string[]
  recommendations: Recommendation[]
  usedFallback: boolean
  /** How the score was produced, shown to the user as inline rich text. */
  methodology: string[]
}

export type ChangeType = 'Grammar' | 'Wording' | 'Alignment'

export type ChangeEdit =
  | { kind: 'replaceLine'; line: number; text: string }
  | { kind: 'appendToLine'; line: number; text: string }
  | { kind: 'appendLines'; lines: string[] }

export interface Change {
  id: string
  type: ChangeType
  labels: string[]
  before: string
  after: string
  note?: string
  acceptedByDefault: boolean
  edit: ChangeEdit
}

export type RichBlock =
  | { kind: 'text'; text: string }
  | { kind: 'quote'; text: string }
  | { kind: 'list'; ordered: boolean; items: string[] }

export interface ChatRequest {
  message: string
  analysis: Analysis | null
}

export const STATUSES = ['Saved', 'Applied', 'Interview', 'Offer', 'Rejected'] as const
export type Status = (typeof STATUSES)[number]

export interface TrackerEntry {
  id: string
  role: string
  company: string
  score: number | null
  status: Status
  date: string
}

export type NewTrackerEntry = Pick<TrackerEntry, 'role' | 'company' | 'score'>

export interface ApiClient {
  documents: {
    /** Resolves to the document's text. Rejects with ApiError if it can't be read. */
    extractText(file: File): Promise<string>
  }
  scoring: {
    analyze(input: ScoreInput): Promise<Analysis>
  }
  improvement: {
    suggest(analysis: Analysis): Promise<Change[]>
  }
  chat: {
    send(request: ChatRequest): Promise<RichBlock[]>
  }
  tracker: {
    list(): Promise<TrackerEntry[]>
    add(entry: NewTrackerEntry): Promise<TrackerEntry>
    updateStatus(id: string, status: Status): Promise<void>
    remove(id: string): Promise<void>
  }
}

/** An error whose message is safe to show to the user. */
export class ApiError extends Error {}
