import type { Analysis, RichBlock } from '../types'
import { GREETING } from '../../lib/greeting'
import { listJoin } from '../../lib/text'

const text = (value: string): RichBlock => ({ kind: 'text', text: value })
const list = (ordered: boolean, items: string[]): RichBlock => ({ kind: 'list', ordered, items })

const NEEDS_ANALYSIS = [text("I don't have an analysis to work from yet. Run a score on the **Score** page and I'll tailor my answers to that job.")]

function explainScore(a: Analysis, role: string) {
  const sorted = a.parts.filter(p => p.score !== null).sort((x, y) => x.score! - y.score!)
  const weakest = sorted[0]
  const strongest = sorted[sorted.length - 1]
  const gaps = a.missing.length
    ? ` The biggest lever is closing skill gaps: ${a.missing.length} required skill${a.missing.length === 1 ? ' is' : 's are'} missing.`
    : ''
  return [text(`You scored **${a.overall}/100** (${a.bandLabel.toLowerCase()}) for **${role}**. Your strongest area is **${strongest.label.toLowerCase()}** (${strongest.score}); the weakest is **${weakest.label.toLowerCase()}** (${weakest.score}).${gaps}`)]
}

function interviewQuestions(a: Analysis, role: string) {
  const questions: string[] = []
  if (a.matched[0]) questions.push(`Walk me through a project where you used ${a.matched[0]}. What was the outcome?`)
  if (a.missing[0]) questions.push(`This role uses ${a.missing[0]}. How would you get up to speed in your first month?`)
  questions.push('Tell me about a time you explained a technical finding to a non-technical audience.')
  if (a.matched[1]) questions.push(`What's a mistake you've made with ${a.matched[1]}, and what did you change afterwards?`)
  questions.push(`Why ${a.company || 'our company'}, and why now?`)
  return [
    text(`Practice questions for **${role}**:`),
    list(true, questions),
    text('Answer each with the STAR format: Situation, Task, Action, Result.'),
  ]
}

function coverLetterOpening(a: Analysis, role: string): RichBlock[] {
  const top = a.matched.slice(0, 2)
  const reason = top.length
    ? `it combines the ${listJoin(top)} work I enjoy most`
    : 'it closely matches the work I want to grow in'
  return [
    text("Here's a draft opening you can adapt:"),
    { kind: 'quote', text: `“I'm applying for the ${role} position${a.company ? ` at ${a.company}` : ''} because ${reason} with problems that matter to your customers. In my most recent role I [one quantified achievement].”` },
    text('Replace the bracket with a real result.'),
  ]
}

export function reply(message: string, a: Analysis | null): RichBlock[] {
  const t = message.toLowerCase()
  const role = a?.title || 'this role'

  if (/^(hi|hello|hey)\b|help|what can you/.test(t)) return GREETING
  if (/missing|keyword|gap|lack/.test(t)) {
    if (!a) return NEEDS_ANALYSIS
    return a.missing.length
      ? [
          text(`For **${role}**, these skills appear in the job description but not in your application:`),
          list(false, a.missing),
          text('Add them only where you have real experience, ideally in a bullet with a measurable result.'),
        ]
      : [text(`Nice: every detected skill for **${role}** already appears in your application.`)]
  }
  if (/cover|letter|opening/.test(t)) return a ? coverLetterOpening(a, role) : NEEDS_ANALYSIS
  if (/interview|question|prepare|prep/.test(t)) return a ? interviewQuestions(a, role) : NEEDS_ANALYSIS
  if (/score|how did i|result|explain|why/.test(t)) return a ? explainScore(a, role) : NEEDS_ANALYSIS
  if (/improve|better|tip|fix|cv|resume|résumé/.test(t)) {
    if (!a) return NEEDS_ANALYSIS
    return [
      text(`Top actions for **${role}**:`),
      list(true, a.recommendations.slice(0, 3).map(r => r.text)),
      text('Open **Improve CV** to apply grammar and wording fixes in one click.'),
    ]
  }
  if (/salary|pay|compensation|negotiat/.test(t)) {
    return [text("I don't have live salary data in this demo. A production version would pull market ranges from a salary data provider. For now, check local salary surveys and the job ad itself.")]
  }
  if (/ats|applicant tracking/.test(t)) {
    return [text('Applicant tracking systems mostly parse plain structure. Use standard headings (Summary, Experience, Education, Skills), avoid tables and images, and mirror the exact skill names from the job description.')]
  }
  return [text("I'm a scripted demo assistant, so I only understand a few topics: your **score**, **missing keywords**, **CV tips**, **cover letter** openings and **interview** questions. Try asking about one of those.")]
}
