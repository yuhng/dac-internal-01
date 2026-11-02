/** Contract between the UI and the backend modules in the architecture reference. */

export interface ScoreInput {
  title: string
  company: string
  jd: string
  cv: string
}

export type Band = 'strong' | 'good' | 'fair' | 'weak'
export type Severity = 'high' | 'med' | 'low'

export interface ScorePart {
  label: string
  weight: number
  score: number
  detail: string
}

export interface Recommendation {
  severity: Severity
  /** Inline rich text, see RichText. */
  text: string
}

export type Tier = 'demonstrated' | 'implied' | 'listed' | 'related' | 'partial' | 'missing' | 'unassessed'

export interface RequirementResult {
  text: string
  kind: 'skill' | 'experience' | 'education'
  importance: 'must' | 'preferred'
  tier: Tier
  /** Null when the requirement could not be assessed and was left out of the score. */
  credit: number | null
  /** The line of the CV that supports this result. */
  evidence: string | null
  method: 'exact' | 'semantic' | null
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
  /** Only the mock falls back to frequent job terms. */
  usedFallback?: boolean
  requirements: RequirementResult[]
  /** How well the CV is written, separate from how well it fits the job. */
  quality: { score: number; parts: ScorePart[] }
  confidence: { level: 'high' | 'medium' | 'low'; reasons: string[] }
  /** The limit that lowered the score, if one did. */
  cap: number | null
  engineVersion: string
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
