import { useEffect, useState, type ChangeEvent, type DragEvent } from 'react'

export function ResumeDropzone({ busy, onFile }: { busy: boolean; onFile(file: File): void }) {
  const [dragging, setDragging] = useState(false)

  // A drop that misses the zone would otherwise make the browser leave the app and open the file.
  useEffect(() => {
    const block = (e: Event) => e.preventDefault()
    window.addEventListener('dragover', block)
    window.addEventListener('drop', block)
    return () => {
      window.removeEventListener('dragover', block)
      window.removeEventListener('drop', block)
    }
  }, [])

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) onFile(file)
  }

  const handleDragLeave = (e: DragEvent<HTMLLabelElement>) => {
    // Moving onto a child element also fires dragleave.
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLLabelElement>) => {
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && !busy) onFile(file)
  }

  return (
    <label
      className={`block rounded-xl border-2 border-dashed px-5 py-10 text-center focus-within:outline-2 focus-within:outline-primary ${busy ? 'cursor-progress' : 'cursor-pointer'} ${dragging ? 'border-primary bg-primary-weak' : 'border-line bg-surface-2 hover:border-primary'}`}
      aria-busy={busy}
      onDragOver={() => setDragging(!busy)}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <span aria-live="polite" className="block text-base font-semibold">
        {busy ? 'Reading your resume…' : dragging ? 'Drop to upload' : 'Drag and drop your resume here'}
      </span>
      <span className="mt-1 block text-[13px] text-muted">
        {busy ? 'Scanned PDFs can take a little longer.' : <>or <span className="font-medium text-primary underline">browse for a file</span> · PDF up to 10 MB</>}
      </span>
      <input type="file" accept=".pdf,application/pdf" aria-label="Upload your resume as a PDF" className="sr-only" disabled={busy} onChange={handleChange} />
    </label>
  )
}
