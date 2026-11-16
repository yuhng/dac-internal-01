import { BAND_LABEL, bandForScore } from '../lib/bands'
import { ApiError, type Analysis, type Recommendation, type RequirementResult, type ResumeDocument, type ScoreInput, type ScorePart } from './types'

const UNREACHABLE = 'The document service could not be reached. Try again in a moment.'
const SCORING_UNREACHABLE = 'The scoring service could not be reached. Try again in a moment.'
export const NEEDS_PDF = 'Upload your CV as a PDF to score it.'

/** PDFs go through OCR v2; the structured document it returns is what scoring needs. */
async function extract(file: File) {
  if (!/\.pdf$/i.test(file.name)) throw new ApiError(`${file.name} isn't a PDF. ${NEEDS_PDF}`)

  const body = new FormData()
  body.append('file', file)

  let response: Response
  try {
    response = await fetch('/api/documents/extract', { method: 'POST', body })
  } catch {
    throw new ApiError(UNREACHABLE)
  }

  // The dev proxy answers with an empty 502 when the backend is down, so the body may not be JSON.
  const result: (ResumeDocument & { detail?: unknown }) | null = await response.json().catch(() => null)
  if (response.ok && result?.text) return { text: result.text, document: result as ResumeDocument }
  throw new ApiError(typeof result?.detail === 'string' ? result.detail : UNREACHABLE)
}

type Importance = 'required' | 'preferred' | 'unspecified'

/** The parts of the scoring v2 response the UI reads (see backend scoring_v2/overall_score.py). */
export interface ScoringV2Response {
  skill_scores: {
    skills: { jd_name: string; importance: Importance; matched: boolean; matches: { original_text: string }[] }[]
    coverage: Record<Importance, { matched: number; requested: number }>
  }
  relevance_scores: { jev_confidence: number | null }
  overall: {
    skill_score_100: number | null
    relevance_score_100: number | null
    overall_score_100: number | null
    method: 'weighted_skills_and_relevance' | 'relevance_only' | null
    provisional: boolean
  }
}

const LOW_CONFIDENCE = 0.6

/** Maps the v2 response onto the Analysis shape the result, chat, improve and tracker pages already use. */
export function toAnalysis(input: ScoreInput, result: ScoringV2Response): Analysis {
  const { skill_scores: skills, relevance_scores: relevance, overall: score } = result
  if (score.overall_score_100 === null || score.relevance_score_100 === null) {
    throw new ApiError('Your experience could not be assessed for this job, so no score was produced. Try again in a moment.')
  }
  const overall = Math.round(score.overall_score_100)
  const band = bandForScore(overall)
  const relevanceOnly = score.method === 'relevance_only'
  const required = skills.coverage.required

  const relevancePart: ScorePart = {
    label: 'Experience relevance', weight: relevanceOnly ? 100 : 60, score: Math.round(score.relevance_score_100),
    detail: 'How closely your work and project experience matches the role',
  }
  const parts: ScorePart[] = relevanceOnly || score.skill_score_100 === null ? [relevancePart] : [
    { label: 'Skills coverage', weight: 40, score: Math.round(score.skill_score_100),
      detail: `${required.matched} of ${required.requested} required skills found` },
    relevancePart,
  ]

  const requirements: RequirementResult[] = skills.skills.map(skill => ({
    text: skill.jd_name,
    kind: 'skill',
    importance: skill.importance === 'required' ? 'must' : 'preferred',
    tier: skill.matched ? 'listed' : 'missing',
    credit: skill.matched ? 1 : 0,
    evidence: skill.matches[0]?.original_text ?? null,
    method: skill.matched ? 'exact' : null,
  }))

  const missing = skills.skills.filter(skill => !skill.matched)
  const recommendations: Recommendation[] = missing.map(skill => ({
    severity: skill.importance === 'required' ? 'high' : 'med',
    text: `Add evidence of **${skill.jd_name}** to your experience or skills, if you have it.`,
  }))
  if (!recommendations.length) {
    recommendations.push({ severity: 'low', text: 'Every skill listed in the job was found in your CV.' })
  }

  const reasons: string[] = []
  if (relevanceOnly) reasons.push('No skills were found in the job description, so this score is based on experience only.')
  else if (score.provisional) reasons.push('The job requirements were extracted automatically and have not been reviewed.')
  const unsure = relevance.jev_confidence !== null && relevance.jev_confidence < LOW_CONFIDENCE
  if (unsure) reasons.push('The experience assessment was uncertain for this match.')

  return {
    ...input,
    id: crypto.randomUUID(),
    overall,
    band,
    bandLabel: BAND_LABEL[band],
    parts,
    matched: skills.skills.filter(skill => skill.matched).map(skill => skill.jd_name),
    missing: missing.map(skill => skill.jd_name),
    recommendations,
    requirements,
    confidence: { level: unsure ? 'low' : reasons.length ? 'medium' : 'high', reasons },
    cap: null,
    engineVersion: 'scoring-v2',
    methodology: relevanceOnly ? [
      '**Experience relevance (100%)**: a model rates how well your work and project experience fits the job.',
      'No skills were extracted from the job description, so skills coverage is left out.',
    ] : [
      '**Skills coverage (40%)**: skills extracted from the job description, matched by exact name or a known alias in your experience and skills sections. Required skills count most, then preferred.',
      '**Experience relevance (60%)**: a model rates how well your work and project experience fits the job.',
    ],
  }
}

async function analyze(input: ScoreInput) {
  if (!input.document) throw new ApiError(NEEDS_PDF)

  let response: Response
  try {
    response = await fetch('/api/scoring/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: input.title, company: input.company, jd: input.jd, document: input.document }),
    })
  } catch {
    throw new ApiError(SCORING_UNREACHABLE)
  }

  const result: (ScoringV2Response & { detail?: unknown }) | null = await response.json().catch(() => null)
  if (response.ok && result) return toAnalysis(input, result)
  if (response.status === 422 && Array.isArray(result?.detail)) {
    const labels: Record<string, string> = { title: 'Job title', company: 'Company', jd: 'Job description', document: 'CV' }
    const messages = result.detail.flatMap(issue => {
      if (!issue || typeof issue.msg !== 'string') return []
      const field = Array.isArray(issue.loc) ? issue.loc[1] : undefined
      return [`${labels[field] ?? 'Request'}: ${issue.msg}`]
    })
    throw new ApiError(messages.join('\n') || 'Check your job description and CV, then try again.')
  }
  throw new ApiError(typeof result?.detail === 'string' ? result.detail : SCORING_UNREACHABLE)
}

export const httpDocuments = { extract }
export const httpScoring = { analyze }
