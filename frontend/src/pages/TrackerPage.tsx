import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { STATUSES, type Status, type TrackerEntry } from '../api/types'
import { Badge, EmptyState, ErrorAlert, Field, PageHead } from '../components/ui'
import { useAddTrackerEntry, useRemoveTrackerEntry, useTrackerEntries, useUpdateTrackerStatus } from '../hooks/useTracker'
import { BAND_BADGE, bandForScore } from '../lib/bands'
import { useToast } from '../state/useToast'

function AddForm() {
  const toast = useToast()
  const addEntry = useAddTrackerEntry()
  const [role, setRole] = useState('')
  const [company, setCompany] = useState('')
  const [error, setError] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const trimmedRole = role.trim()
    const trimmedCompany = company.trim()
    if (!trimmedRole || !trimmedCompany) {
      setError('Enter both a role and a company.')
      return
    }
    setError('')
    addEntry.mutate({ role: trimmedRole, company: trimmedCompany, score: null }, {
      onSuccess: () => {
        setRole('')
        setCompany('')
        toast('Application added')
      },
    })
  }

  return (
    <div className="card mb-5">
      <form className="grid items-end gap-2.5 sm:grid-cols-[1fr_1fr_auto]" onSubmit={submit} noValidate>
        <Field label="Role">
          <input className="input" type="text" placeholder="e.g. Product Analyst" value={role} onChange={e => setRole(e.target.value)} />
        </Field>
        <Field label="Company">
          <input className="input" type="text" placeholder="e.g. Acme Corp" value={company} onChange={e => setCompany(e.target.value)} />
        </Field>
        <button type="submit" className="btn">Add manually</button>
      </form>
      {error && <div className="mt-2.5"><ErrorAlert>{error}</ErrorAlert></div>}
    </div>
  )
}

function EntryRow({ entry }: { entry: TrackerEntry }) {
  const toast = useToast()
  const updateStatus = useUpdateTrackerStatus()
  const removeEntry = useRemoveTrackerEntry()

  const changeStatus = (status: Status) =>
    updateStatus.mutate({ id: entry.id, status }, { onSuccess: () => toast(`Status updated to ${status}`) })

  return (
    <tr>
      <td className="table-cell">{entry.role}</td>
      <td className="table-cell">{entry.company}</td>
      <td className="table-cell">
        {entry.score === null
          ? <span className="text-muted">Not scored</span>
          : <Badge className={BAND_BADGE[bandForScore(entry.score)]}>{entry.score}</Badge>}
      </td>
      <td className="table-cell">
        <select aria-label={`Status of ${entry.role}`} className="input !w-auto !px-2 !py-[5px]" value={entry.status} onChange={e => changeStatus(e.target.value as Status)}>
          {STATUSES.map(status => <option key={status}>{status}</option>)}
        </select>
      </td>
      <td className="table-cell text-muted">{entry.date}</td>
      <td className="table-cell">
        <button
          type="button"
          className="btn btn-sm border-transparent! bg-transparent!"
          aria-label={`Remove ${entry.role}`}
          onClick={() => removeEntry.mutate(entry.id, { onSuccess: () => toast('Application removed') })}
        >
          Remove
        </button>
      </td>
    </tr>
  )
}

export function TrackerPage() {
  const { data: entries = [], error } = useTrackerEntries()

  return (
    <>
      <PageHead title="Application Tracker" subtitle="Keep every scored application in one place." />
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {STATUSES.map(status => (
          <div key={status} className="rounded-xl border border-line bg-surface px-4 py-3.5">
            <b className="block text-2xl">{entries.filter(e => e.status === status).length}</b>
            <span className="text-[13px] text-muted">{status}</span>
          </div>
        ))}
      </div>
      <AddForm />
      <div className="card">
        {error && <ErrorAlert>{error.message}</ErrorAlert>}
        {!error && !entries.length && (
          <EmptyState icon="▤" title="No applications yet">
            <p className="text-[13px]">Score an application and click <b>Save to tracker</b>, or add one manually above.</p>
            <Link className="btn mt-4" to="/score">Score an application</Link>
          </EmptyState>
        )}
        {entries.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className="table-head">Role</th>
                  <th className="table-head">Company</th>
                  <th className="table-head">Match</th>
                  <th className="table-head">Status</th>
                  <th className="table-head">Added</th>
                  <th className="table-head" aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {entries.map(entry => <EntryRow key={entry.id} entry={entry} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
