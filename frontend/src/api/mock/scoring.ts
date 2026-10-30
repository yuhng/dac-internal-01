import type { Analysis, Band, Change, Recommendation, ScoreInput, ScorePart } from '../types'
import { countWords, listJoin } from '../../lib/text'
import { SKILLS, SPELLING, STOP_WORDS, WEAK_PHRASES } from './data'

const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&')
const hasTerm = (text: string, term: string) =>
  new RegExp(`(?:^|[^a-z0-9])${escapeRegExp(term)}(?:$|[^a-z0-9])`).test(text)
const tokens = (text: string) =>
  text.toLowerCase().split(/[^a-z0-9+#]+/).filter(w => w.length > 2 && !STOP_WORDS.has(w) && !/^\d+$/.test(w))

function frequencies(text: string) {
  const counts: Record<string, number> = {}
  for (const word of tokens(text)) counts[word] = (counts[word] ?? 0) + 1
  return counts
}

const findSkills = (lowerText: string) =>
  SKILLS.filter(([, ...terms]) => terms.some(t => hasTerm(lowerText, t))).map(([name]) => name)

function matchesSkill(name: string, lowerText: string) {
  const entry = SKILLS.find(([skill]) => skill === name)
  return entry ? entry.slice(1).some(t => hasTerm(lowerText, t)) : hasTerm(lowerText, name.toLowerCase())
}

const topTerms = (text: string, n: number) =>
  Object.entries(frequencies(text)).sort((a, b) => b[1] - a[1]).slice(0, n).map(([term]) => term)

function cosine(a: string, b: string) {
  const fa = frequencies(a)
  const fb = frequencies(b)
  let dot = 0
  let na = 0
  let nb = 0
  for (const k in fa) {
    na += fa[k] ** 2
    if (fb[k]) dot += fa[k] * fb[k]
  }
  for (const k in fb) nb += fb[k] ** 2
  return na && nb ? dot / Math.sqrt(na * nb) : 0
}

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

const SECTIONS: [string, RegExp][] = [
  ['Summary', /^(summary|profile|professional summary|objective)\b/im],
  ['Experience', /^(experience|work experience|employment|work history)\b/im],
  ['Education', /^education\b/im],
  ['Skills', /^(skills|technical skills|core skills)\b/im],
  ['Projects / certifications', /^(projects|certifications|achievements|awards)\b/im],
]

const bandFor = (score: number): [Band, string] =>
  score >= 80 ? ['strong', 'Strong match']
    : score >= 60 ? ['good', 'Good match']
      : score >= 40 ? ['fair', 'Fair match']
        : ['weak', 'Weak match']

const METHODOLOGY = [
  `**Skills match (40%)**: skills from a built-in dictionary of ${SKILLS.length} skills are found in the job description and checked against your CV and cover letter.`,
  '**Content similarity (20%)**: cosine similarity of word frequencies between CV and job description.',
  '**Cover letter (15%)**: job skills referenced, company and title named, and length.',
  '**Impact (15%)**: share of bullet points with numbers, minus weak phrasing.',
  '**Structure (10%)**: presence of standard CV sections and sensible length.',
  'These weights are placeholders. A production scoring method still needs to be defined and validated.',
]

export function analyze(input: ScoreInput): Analysis {
  const { jd, cv, cl, title, company } = input
  const jdLower = jd.toLowerCase()
  const cvLower = cv.toLowerCase()
  const clLower = cl.toLowerCase()

  let requirements = findSkills(jdLower)
  const usedFallback = requirements.length < 3
  if (usedFallback) requirements = topTerms(jd, 10)
  const matched = requirements.filter(s => matchesSkill(s, `${cvLower}\n${clLower}`))
  const missing = requirements.filter(s => !matched.includes(s))
  const skillScore = Math.round((matched.length / requirements.length) * 100)

  const similarity = cosine(jd, cv)
  const overlapScore = Math.min(100, Math.round((similarity / 0.45) * 100))

  const bullets = cv.split('\n').filter(l => /^\s*[-•*]/.test(l))
  const quantified = bullets.filter(l => /\d/.test(l))
  const lineChanges = computeLineChanges(cv)
  const weakCount = lineChanges.filter(c => c.type === 'Wording').length
  const grammarCount = lineChanges.reduce((n, c) => n + c.labels.filter(l => !l.startsWith('“')).length, 0)
  const impactScore = bullets.length
    ? Math.max(0, Math.min(100, Math.round((quantified.length / bullets.length / 0.6) * 100)) - weakCount * 5)
    : 20

  const missingSections = SECTIONS.filter(([, re]) => !re.test(cv)).map(([name]) => name)
  const cvWords = countWords(cv)
  let structureScore = Math.round(((SECTIONS.length - missingSections.length) / SECTIONS.length) * 100)
  if (cvWords < 150 || cvWords > 1100) structureScore = Math.max(0, structureScore - 20)

  let clScore: number | null = null
  let clDetail = 'Not provided — excluded from the overall score'
  const clMentionsCompany = Boolean(company) && clLower.includes(company.toLowerCase())
  if (cl.trim()) {
    const clSkills = requirements.filter(s => matchesSkill(s, clLower))
    const clWords = countWords(cl)
    clScore = Math.round(Math.min(1, clSkills.length / Math.min(5, requirements.length)) * 50)
      + (clMentionsCompany ? 20 : 0)
      + (title && clLower.includes(title.toLowerCase()) ? 15 : 0)
      + (clWords >= 120 && clWords <= 450 ? 15 : clWords >= 60 ? 8 : 0)
    clDetail = `${clSkills.length} job skills referenced · ${clWords} words · ${clMentionsCompany ? 'mentions' : 'does not mention'} the company`
  }

  const parts: ScorePart[] = [
    { label: 'Skills match', weight: 40, score: skillScore, detail: `${matched.length} of ${requirements.length} ${usedFallback ? 'key terms' : 'required skills'} found` },
    { label: 'Content similarity', weight: 20, score: overlapScore, detail: `Term-overlap similarity ${similarity.toFixed(2)} between CV and job description` },
    { label: 'Cover letter alignment', weight: 15, score: clScore, detail: clDetail },
    { label: 'Impact & wording', weight: 15, score: impactScore, detail: `${quantified.length} of ${bullets.length} bullet points quantified · ${weakCount} weak phrase${weakCount === 1 ? '' : 's'}` },
    { label: 'Structure', weight: 10, score: structureScore, detail: missingSections.length ? `Missing: ${missingSections.join(', ')}` : 'All key sections present' },
  ]
  const scored = parts.filter(p => p.score !== null)
  const overall = Math.round(
    scored.reduce((sum, p) => sum + p.score! * p.weight, 0) / scored.reduce((sum, p) => sum + p.weight, 0),
  )
  const [band, bandLabel] = bandFor(overall)

  const recommendations: Recommendation[] = []
  const recommend = (severity: Recommendation['severity'], text: string) => recommendations.push({ severity, text })
  if (missing.length) recommend('high', `Add evidence of **${listJoin(missing.slice(0, 4))}** if you have it. These appear in the job description but not in your application.`)
  if (bullets.length && quantified.length / bullets.length < 0.6) recommend('med', `Quantify more achievements. Only ${quantified.length} of ${bullets.length} bullet points include a number, percentage or scale.`)
  if (weakCount) recommend('med', `Replace ${weakCount} passive phrase${weakCount === 1 ? '' : 's'} such as “responsible for” with action verbs.`)
  if (grammarCount) recommend('med', `Fix ${grammarCount} spelling or grammar issue${grammarCount === 1 ? '' : 's'}. See **Improve CV**.`)
  if (!cl.trim()) recommend('low', 'Add a cover letter. It contributes 15% of the score and lets you explain gaps directly.')
  else if (company && !clMentionsCompany) recommend('low', `Mention ${company} by name in your cover letter.`)
  if (missingSections.length) recommend('low', `Consider adding a ${missingSections[0]} section.`)
  if (!recommendations.length) recommend('low', 'Your application is well aligned. Tailor your opening line to the company before sending.')

  return {
    ...input,
    id: crypto.randomUUID(),
    overall,
    band,
    bandLabel,
    parts,
    matched,
    missing,
    recommendations,
    usedFallback,
    methodology: METHODOLOGY,
  }
}
