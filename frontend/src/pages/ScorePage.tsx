import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { ApiError, type ScoreInput } from '../api/types'
import { ResultPanel } from '../components/ResultPanel'
import { ErrorAlert, Field, PageHead } from '../components/ui'
import { SAMPLES } from '../lib/samples'
import { countWords } from '../lib/text'
import { trimInput, useApplication } from '../state/useApplication'
import { useToast } from '../state/useToast'

export type ScoreFocus = 'analyze' | 'title'

const MIN_JD_WORDS = 30
const MIN_CV_WORDS = 50

function validate({ jd, cv }: ScoreInput) {
  const errors: string[] = []
  if (!jd) errors.push('Paste a job description.')
  else if (countWords(jd) < MIN_JD_WORDS) errors.push(`The job description is too short (${countWords(jd)} words). Paste at least ${MIN_JD_WORDS} words so requirements can be extracted.`)
  if (!cv) errors.push('Paste your CV or upload a .txt file.')
  else if (countWords(cv) < MIN_CV_WORDS) errors.push(`Your CV is too short to score (${countWords(cv)} words, minimum ${MIN_CV_WORDS}).`)
  return errors
}

function WordCount({ text }: { text: string }) {
  const n = countWords(text)
  return n ? <span className="text-xs font-normal text-muted">· {n} words</span> : null
}

function UploadButton({ onFile }: { onFile(file: File): void }) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) onFile(file)
  }
  return (
    <label className="btn btn-sm focus-within:outline-2 focus-within:outline-primary">
      Upload .txt
      <input type="file" accept=".txt,text/plain" className="sr-only" onChange={handleChange} />
    </label>
  )
}

export function ScorePage() {
  const { draft, updateDraft, runAnalysis, isAnalyzing, reset } = useApplication()
  const toast = useToast()
  const [sample, setSample] = useState(0)
  const [errors, setErrors] = useState<string[]>([])

  const location = useLocation()
  const titleRef = useRef<HTMLInputElement>(null)
  const analyzeRef = useRef<HTMLButtonElement>(null)
  const focus = (location.state as { focus?: ScoreFocus } | null)?.focus
  useEffect(() => {
    if (focus === 'title') titleRef.current?.focus()
    if (focus === 'analyze') analyzeRef.current?.focus()
  }, [focus])

  const loadSample = () => {
    updateDraft(SAMPLES[sample])
    setErrors([])
    toast('Sample loaded. Click “Analyze match”.')
  }

  const upload = async (field: 'cv' | 'cl', file: File) => {
    try {
      updateDraft({ [field]: await api.documents.extractText(file) })
      setErrors([])
      toast(`Loaded ${file.name}`)
    } catch (err) {
      setErrors([err instanceof ApiError ? err.message : 'The file could not be read. Try pasting the text instead.'])
    }
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (isAnalyzing) return
    const input = trimInput(draft)
    const problems = validate(input)
    setErrors(problems)
    if (!problems.length) runAnalysis(input)
  }

  const clear = () => {
    reset()
    setErrors([])
  }

  return (
    <>
      <PageHead
        title="CV & Cover Letter Scoring"
        subtitle="See how closely your application matches a specific job."
        actions={
          <>
            <select aria-label="Sample job" className="input !w-auto" value={sample} onChange={e => setSample(Number(e.target.value))}>
              {SAMPLES.map((s, i) => <option key={s.title} value={i}>Sample: {s.title}</option>)}
            </select>
            <button type="button" className="btn" onClick={loadSample}>Load sample</button>
          </>
        }
      />
      <div className="grid items-start gap-5 lg:grid-cols-2">
        <form className="card min-w-0 space-y-3.5" onSubmit={submit} noValidate>
          <div>
            <h2 className="mb-2.5 font-semibold">1. Target job</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Job title">
                <input ref={titleRef} className="input" type="text" placeholder="e.g. Data Analyst" value={draft.title} onChange={e => updateDraft({ title: e.target.value })} />
              </Field>
              <Field label="Company">
                <input className="input" type="text" placeholder="e.g. Northwind Retail" value={draft.company} onChange={e => updateDraft({ company: e.target.value })} />
              </Field>
            </div>
          </div>
          <Field label="Job description" hint={<WordCount text={draft.jd} />}>
            <textarea className="input" rows={7} placeholder="Paste the full job description, including responsibilities and requirements." value={draft.jd} onChange={e => updateDraft({ jd: e.target.value })} />
          </Field>
          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h2 className="font-semibold">2. Your CV <WordCount text={draft.cv} /></h2>
              <UploadButton onFile={file => upload('cv', file)} />
            </div>
            <textarea aria-label="Your CV" className="input" rows={10} placeholder="Paste your CV as plain text." value={draft.cv} onChange={e => updateDraft({ cv: e.target.value })} />
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h2 className="font-semibold">3. Cover letter <span className="text-[13px] font-normal text-muted">(optional)</span> <WordCount text={draft.cl} /></h2>
              <UploadButton onFile={file => upload('cl', file)} />
            </div>
            <textarea aria-label="Cover letter" className="input" rows={6} placeholder="Paste your cover letter. Leave blank to score the CV only." value={draft.cl} onChange={e => updateDraft({ cl: e.target.value })} />
          </div>
          {errors.length > 0 && <ErrorAlert>{errors.map(error => <div key={error}>{error}</div>)}</ErrorAlert>}
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" className="btn" onClick={clear}>Clear</button>
            <button ref={analyzeRef} type="submit" className="btn btn-primary" disabled={isAnalyzing}>
              {isAnalyzing ? 'Analyzing…' : 'Analyze match'}
            </button>
          </div>
        </form>
        <ResultPanel onLoadSample={loadSample} />
      </div>
    </>
  )
}
