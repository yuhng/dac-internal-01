import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { ApiError } from '../api/types'
import { ResumeDropzone } from '../components/ResumeDropzone'
import { ErrorAlert } from '../components/ui'
import { useTrackerEntries } from '../hooks/useTracker'
import { SAMPLES } from '../lib/samples'
import { useApplication } from '../state/useApplication'
import { useToast } from '../state/useToast'
import type { ScoreFocus } from './ScorePage'

const FLOW = [
  { to: '/score', title: 'Score', text: 'Paste a job description and CV. Get a match score with a breakdown.' },
  { to: '/improve', title: 'Improve', text: 'Review grammar fixes, stronger wording and keyword alignment. Accept what fits.' },
  { to: '/assistant', title: 'Ask', text: 'Ask the assistant about your gaps, cover letter openings or interview prep.' },
  { to: '/tracker', title: 'Track', text: 'Save scored applications and move them through your pipeline.' },
]

const CAPABILITIES = [
  ['Match scoring', 'Keyword dictionary, term-overlap similarity and rule checks', 'Trained NLP / embedding model, validated against hiring outcomes'],
  ['CV improvements', 'Regex grammar and wording rules, keyword insertion', 'LLM rewriting with a factual-consistency check'],
  ['Assistant', 'Scripted intents using your latest analysis', 'LLM chat grounded in your documents'],
  ['File upload', 'PDF (with OCR for scans) and .txt', 'DOCX parsing and stored uploads'],
  ['Tracker', 'Saved in this browser (localStorage)', 'User accounts and a database'],
]

function Activity() {
  const { analysis } = useApplication()
  const { data: entries = [] } = useTrackerEntries()
  if (!analysis && !entries.length) return null

  const scored = entries.filter(e => e.score !== null)
  const inProgress = entries.filter(e => e.status === 'Applied' || e.status === 'Interview').length
  const stats = [
    { value: analysis ? analysis.overall : '—', label: analysis ? `Latest score · ${analysis.title || 'Untitled role'}` : 'Latest score' },
    { value: entries.length, label: 'Tracked applications' },
    { value: inProgress, label: 'Applied or interviewing' },
    { value: scored.length ? Math.round(scored.reduce((sum, e) => sum + e.score!, 0) / scored.length) : '—', label: 'Average tracked score' },
  ]

  return (
    <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
      {stats.map(stat => (
        <div key={stat.label} className="min-w-0 rounded-xl border border-line bg-surface px-4 py-3.5">
          <b className="block text-2xl">{stat.value}</b>
          <span className="block truncate text-[13px] text-muted">{stat.label}</span>
        </div>
      ))}
    </div>
  )
}

export function OverviewPage() {
  const { updateDraft } = useApplication()
  const toast = useToast()
  const navigate = useNavigate()
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const goToScore = (focus: ScoreFocus) => navigate('/score', { state: { focus } })
  const startWithSample = () => {
    updateDraft(SAMPLES[0])
    goToScore('analyze')
    toast('Sample loaded. Click “Analyze match”.')
  }

  const parseResume = async (file: File) => {
    if (!/\.pdf$/i.test(file.name)) {
      setError(`${file.name} isn't a PDF. Upload a PDF, or paste your CV instead.`)
      return
    }
    setParsing(true)
    setError(null)
    try {
      updateDraft({ cv: await api.documents.extractText(file) })
      goToScore('title')
      toast(`Loaded ${file.name}. Now add the job you're targeting.`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The file could not be read. Try pasting the text instead.')
    } finally {
      setParsing(false)
    }
  }

  return (
    <>
      <div className="card p-5! sm:p-7!">
        <h1 className="mb-4 text-[28px] leading-tight font-[650]">Know how well your application matches the job before you hit send.</h1>
        <ResumeDropzone busy={parsing} onFile={parseResume} />
        {error && <div className="mt-3"><ErrorAlert>{error}</ErrorAlert></div>}
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="btn btn-sm" onClick={() => goToScore('title')}>Paste my CV instead</button>
          <button type="button" className="btn btn-sm" onClick={startWithSample}>Try with sample data</button>
        </div>
      </div>

      <Activity />

      <div className="mt-5 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
        {FLOW.map(({ to, title, text }, i) => (
          <Link key={to} to={to} className="card block p-4! hover:border-primary">
            <div className="mb-2.5 grid size-[26px] place-items-center rounded-full bg-primary-weak text-[13px] font-bold text-primary">{i + 1}</div>
            <h2 className="mb-1 font-semibold">{title}</h2>
            <p className="text-[13px] text-muted">{text}</p>
          </Link>
        ))}
      </div>

      <div className="card mt-5">
        <h2 className="font-semibold">What's real and what's simulated in this demo</h2>
        <div className="mt-2.5 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="table-head">Capability</th>
                <th className="table-head">In this demo</th>
                <th className="table-head">In production</th>
              </tr>
            </thead>
            <tbody>
              {CAPABILITIES.map(([capability, demo, production]) => (
                <tr key={capability}>
                  <td className="table-cell font-medium">{capability}</td>
                  <td className="table-cell">{demo}</td>
                  <td className="table-cell">{production}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
