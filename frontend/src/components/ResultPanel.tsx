import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Analysis, RequirementResult, Tier } from '../api/types'
import { useAddTrackerEntry } from '../hooks/useTracker'
import { BAND_BADGE } from '../lib/bands'
import { useApplication } from '../state/useApplication'
import { useToast } from '../state/useToast'
import { InlineText } from './RichText'
import { Badge, EmptyState, SimulatedBadge } from './ui'

const STEPS = ['Reading your CV', 'Extracting job requirements', 'Matching skills', 'Assessing experience relevance']
const STEP_MS = 350

const TIER: Record<Tier, { label: string; className: string }> = {
  demonstrated: { label: 'Shown in your work', className: 'text-success' },
  implied: { label: 'Implied by your work', className: 'text-success' },
  listed: { label: 'Mentioned only', className: 'text-primary' },
  related: { label: 'Related skill', className: 'text-warn' },
  partial: { label: 'Partly met', className: 'text-warn' },
  missing: { label: 'Not found', className: 'text-danger' },
  unassessed: { label: 'Not assessed', className: 'text-muted' },
}

const RING_COLOR: Record<Analysis['band'], string> = {
  strong: 'var(--success)',
  good: 'var(--primary)',
  fair: 'var(--warn)',
  weak: 'var(--danger)',
}

const SectionTitle = ({ children }: { children: string }) => (
  <h4 className="mt-[22px] mb-2.5 text-[13px] font-semibold tracking-[.04em] text-muted uppercase">{children}</h4>
)

function AnalyzingSteps() {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setStep(s => Math.min(s + 1, STEPS.length)), STEP_MS)
    return () => clearInterval(timer)
  }, [])

  return (
    <EmptyState title="Analyzing your application">
      <p className="text-[13px]">Comparing your CV with the job</p>
      <ul className="mx-auto mt-5 max-w-[300px] text-left">
        {STEPS.map((label, i) => (
          <li key={label} className={`flex items-center gap-2.5 py-1.5 ${i < step ? 'text-ink' : ''}`}>
            <span
              className={`size-4 flex-none rounded-full border-2 ${
                i < step ? 'border-success bg-success'
                  : i === step ? 'animate-spin border-primary border-t-transparent motion-reduce:animate-none'
                    : 'border-line'
              }`}
            />
            {label}
          </li>
        ))}
      </ul>
    </EmptyState>
  )
}

function ScoreRing({ analysis }: { analysis: Analysis }) {
  return (
    <div
      role="img"
      aria-label={`Match score ${analysis.overall} out of 100`}
      className="grid size-[108px] flex-none place-items-center rounded-full"
      style={{ background: `conic-gradient(${RING_COLOR[analysis.band]} ${analysis.overall}%, var(--surface-2) 0)` }}
    >
      <div className="grid size-[84px] place-items-center rounded-full bg-surface text-center text-[28px] leading-tight font-bold">
        <div>
          {analysis.overall}
          <small className="block text-[11px] font-medium text-muted">/ 100</small>
        </div>
      </div>
    </div>
  )
}

function Parts({ parts }: { parts: Analysis['parts'] }) {
  return (
    <div className="grid gap-3">
      {parts.map(part => (
        <div key={part.label} className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 text-sm">
          <span>{part.label} <span className="text-[13px] text-muted">({part.weight}%)</span></span>
          <b>{part.score ?? '—'}</b>
          <div className="col-span-full h-[7px] overflow-hidden rounded-full bg-surface-2">
            <i className="block h-full rounded-full bg-primary" style={{ width: `${part.score ?? 0}%` }} />
          </div>
          <span className="col-span-full text-xs text-muted">{part.detail}</span>
        </div>
      ))}
    </div>
  )
}

function RequirementRow({ requirement }: { requirement: RequirementResult }) {
  const tier = TIER[requirement.tier]
  return (
    <li className="rounded-lg bg-surface-2 px-3 py-2.5 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <span>{requirement.text}{requirement.importance === 'must' && <span className="text-[13px] text-muted"> · must-have</span>}</span>
        <span className={`text-[13px] font-medium ${tier.className}`}>{tier.label}</span>
      </div>
      {requirement.evidence && <p className="mt-1 text-[13px] text-muted">{requirement.evidence}</p>}
    </li>
  )
}

function Result({ analysis }: { analysis: Analysis }) {
  const { prevScore, stale } = useApplication()
  const toast = useToast()
  const addEntry = useAddTrackerEntry()
  const delta = prevScore !== null ? analysis.overall - prevScore : null

  const saveToTracker = () => addEntry.mutate(
    { role: analysis.title || 'Untitled role', company: analysis.company || '—', score: analysis.overall },
    { onSuccess: () => toast('Saved to tracker') },
  )

  return (
    <>
      {stale && (
        <div className="mb-3.5 rounded-lg bg-warn-weak px-3 py-2.5 text-sm text-warn">
          Inputs have changed since this analysis. Click <b>Analyze match</b> to refresh.
        </div>
      )}
      <div className="flex flex-col items-start gap-[18px] sm:flex-row sm:items-center">
        <ScoreRing analysis={analysis} />
        <div>
          <Badge className={BAND_BADGE[analysis.band]}>{analysis.bandLabel}</Badge>{' '}
          {analysis.engineVersion !== 'scoring-v2' && <SimulatedBadge>Rule-based score</SimulatedBadge>}
          <h3 className="mt-2 text-lg font-semibold">
            {analysis.title || 'Untitled role'}{analysis.company && ` · ${analysis.company}`}
          </h3>
          {delta !== null && (
            <div className={`mt-1 text-[13px] font-semibold ${delta < 0 ? 'text-danger' : 'text-success'}`}>
              {delta >= 0 ? `▲ +${delta}` : `▼ ${delta}`} points vs. previous version
            </div>
          )}
          {analysis.cap !== null && (
            <p className="mt-1 text-[13px] text-muted">Limited to {analysis.cap} because of missing must-haves.</p>
          )}
          {analysis.confidence.level !== 'high' && (
            <p className="mt-1 text-[13px] text-muted">
              <b className="font-medium capitalize">{analysis.confidence.level} confidence.</b> {analysis.confidence.reasons.join(' ')}
            </p>
          )}
        </div>
      </div>

      <SectionTitle>Score breakdown</SectionTitle>
      <Parts parts={analysis.parts} />

      <SectionTitle>Skills from the job description</SectionTitle>
      <div className="flex flex-wrap gap-1.5">
        {analysis.matched.map(skill => (
          <span key={skill} className="rounded-full bg-success-weak px-2.5 py-[3px] text-[13px] text-success">✓ {skill}</span>
        ))}
        {analysis.missing.map(skill => (
          <span key={skill} className="rounded-full bg-warn-weak px-2.5 py-[3px] text-[13px] text-warn">✕ {skill}</span>
        ))}
      </div>

      <SectionTitle>Evidence from your CV</SectionTitle>
      <ul className="grid gap-2">
        {analysis.requirements.map(requirement => <RequirementRow key={`${requirement.kind}:${requirement.text}`} requirement={requirement} />)}
      </ul>

      {analysis.quality && (
        <>
          <SectionTitle>{`CV quality: ${analysis.quality.score} / 100`}</SectionTitle>
          <Parts parts={analysis.quality.parts} />
        </>
      )}

      <div className="mt-[18px] flex flex-wrap justify-end gap-2">
        <button type="button" className="btn" onClick={saveToTracker}>Save to tracker</button>
        <Link className="btn" to="/assistant">Ask assistant</Link>
        <Link className="btn btn-primary" to="/improve">Improve my CV →</Link>
      </div>

      <details className="mt-[18px] text-[13px] text-muted">
        <summary className="cursor-pointer font-medium text-ink">How is this score calculated?</summary>
        <ul className="mt-2 list-disc space-y-1 pl-[18px]">
          {analysis.methodology.map(line => <li key={line}><InlineText text={line} /></li>)}
        </ul>
      </details>
    </>
  )
}

export function ResultPanel({ onLoadSample }: { onLoadSample(): void }) {
  const { analysis, isAnalyzing, analysisError, retryAnalysis } = useApplication()

  let content
  if (isAnalyzing) {
    content = <AnalyzingSteps />
  } else if (analysisError) {
    content = (
      <EmptyState icon="!" title="Analysis failed">
        <p className="text-[13px]">{analysisError}</p>
        <button type="button" className="btn mt-4" onClick={retryAnalysis}>Try again</button>
      </EmptyState>
    )
  } else if (analysis) {
    content = <Result analysis={analysis} />
  } else {
    content = (
      <EmptyState icon="◎" title="No analysis yet">
        <p className="text-[13px]">
          Add a job description and upload your CV as a PDF, then click <b>Analyze match</b>.
          <br />
          No job description handy? Load a sample job.
        </p>
        <button type="button" className="btn mt-4" onClick={onLoadSample}>Load sample job</button>
      </EmptyState>
    )
  }

  return <div className="card lg:sticky lg:top-5" aria-live="polite">{content}</div>
}
