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
  { to: '/score', title: 'Score', text: 'Paste a job description and upload your CV as a PDF. Get a match score with a breakdown.' },
  { to: '/improve', title: 'Improve', text: 'Review grammar fixes, stronger wording and keyword alignment. Accept what fits.' },
  { to: '/assistant', title: 'Ask', text: 'Ask the assistant about your gaps, cover letter openings or interview prep.' },
  { to: '/tracker', title: 'Track', text: 'Save scored applications and move them through your pipeline.' },
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
    const { title, company, jd } = SAMPLES[0]
    updateDraft({ title, company, jd })
    goToScore('analyze')
    toast('Sample job loaded. Upload your CV as a PDF to score it.')
  }

  const parseResume = async (file: File) => {
    if (!/\.pdf$/i.test(file.name)) {
      setError(`${file.name} isn't a PDF. Upload your CV as a PDF.`)
      return
    }
    setParsing(true)
    setError(null)
    try {
      const { text, document } = await api.documents.extract(file)
      updateDraft({ cv: text, document })
      goToScore('title')
      toast(`Loaded ${file.name}. Now add the job you're targeting.`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The file could not be read. Try another PDF.')
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
          <button type="button" className="btn btn-sm" onClick={startWithSample}>Try a sample job</button>
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
    </>
  )
}
