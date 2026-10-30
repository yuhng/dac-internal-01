import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Analysis, Severity } from '../api/types'
import { useAddTrackerEntry } from '../hooks/useTracker'
import { BAND_BADGE } from '../lib/bands'
import { useApplication } from '../state/useApplication'
import { useToast } from '../state/useToast'
import { InlineText } from './RichText'
import { Badge, EmptyState, SimulatedBadge } from './ui'

const STEPS = ['Parsing documents', 'Extracting job requirements', 'Matching skills and keywords', 'Scoring impact and structure']
const STEP_MS = 350

const SEVERITY: Record<Severity, { label: string; className: string }> = {
  high: { label: 'High', className: 'bg-danger-weak text-danger' },
  med: { label: 'Medium', className: 'bg-warn-weak text-warn' },
  low: { label: 'Low', className: 'bg-primary-weak text-primary' },
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
      <p className="text-[13px]">Running locally in your browser</p>
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
          <SimulatedBadge>Heuristic score</SimulatedBadge>
          <h3 className="mt-2 text-lg font-semibold">
            {analysis.title || 'Untitled role'}{analysis.company && ` · ${analysis.company}`}
          </h3>
          {delta !== null && (
            <div className={`mt-1 text-[13px] font-semibold ${delta < 0 ? 'text-danger' : 'text-success'}`}>
              {delta >= 0 ? `▲ +${delta}` : `▼ ${delta}`} points vs. previous version
            </div>
          )}
          {analysis.usedFallback && (
            <p className="mt-1 text-[13px] text-muted">Few known skills were detected, so the most frequent job terms were used instead.</p>
          )}
        </div>
      </div>

      <SectionTitle>Score breakdown</SectionTitle>
      <div className="grid gap-3">
        {analysis.parts.map(part => (
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

      <SectionTitle>Skills from the job description</SectionTitle>
      <div className="flex flex-wrap gap-1.5">
        {analysis.matched.map(skill => (
          <span key={skill} className="rounded-full bg-success-weak px-2.5 py-[3px] text-[13px] text-success">✓ {skill}</span>
        ))}
        {analysis.missing.map(skill => (
          <span key={skill} className="rounded-full bg-warn-weak px-2.5 py-[3px] text-[13px] text-warn">✕ {skill}</span>
        ))}
      </div>

      <SectionTitle>Recommendations</SectionTitle>
      <ul className="grid gap-2">
        {analysis.recommendations.map(rec => (
          <li key={rec.text} className="flex gap-2.5 rounded-lg bg-surface-2 px-3 py-2.5 text-sm">
            <span className={`h-fit flex-none rounded px-1.5 py-0.5 text-[11px] font-bold uppercase ${SEVERITY[rec.severity].className}`}>
              {SEVERITY[rec.severity].label}
            </span>
            <span><InlineText text={rec.text} /></span>
          </li>
        ))}
      </ul>

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
          Add a job description and your CV, then click <b>Analyze match</b>.
          <br />
          No documents handy? Load a sample.
        </p>
        <button type="button" className="btn mt-4" onClick={onLoadSample}>Load sample data</button>
      </EmptyState>
    )
  }

  return <div className="card lg:sticky lg:top-5" aria-live="polite">{content}</div>
}
