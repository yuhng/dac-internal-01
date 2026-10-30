import { useMutation } from '@tanstack/react-query'
import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { Analysis, ScoreInput } from '../api/types'
import { ApplicationContext, trimInput, type ApplicationState, type ChatMessage } from './useApplication'

const EMPTY_DRAFT: ScoreInput = { title: '', company: '', jd: '', cv: '', cl: '' }

/** Session state shared across pages, so nothing is lost when navigating between them. */
export function ApplicationProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState(EMPTY_DRAFT)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [prevScore, setPrevScore] = useState<number | null>(null)
  const [selection, setSelection] = useState<Record<string, boolean>>({})
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [lastRun, setLastRun] = useState<{ input: ScoreInput; prevScore: number | null } | null>(null)

  const mutation = useMutation({ mutationFn: api.scoring.analyze })
  const { mutate, reset: resetMutation } = mutation

  const runAnalysis = useCallback((input: ScoreInput, previous: number | null = null) => {
    setLastRun({ input, prevScore: previous })
    mutate(input, {
      onSuccess: result => {
        setAnalysis(result)
        setPrevScore(previous)
        setSelection({})
      },
      onError: () => setAnalysis(null),
    })
  }, [mutate])

  const value = useMemo<ApplicationState>(() => {
    const current = analysis && trimInput(analysis)
    const trimmed = trimInput(draft)
    return {
      draft,
      updateDraft: patch => setDraft(d => ({ ...d, ...patch })),
      analysis,
      prevScore,
      stale: !!current && (Object.keys(trimmed) as (keyof ScoreInput)[]).some(k => trimmed[k] !== current[k]),
      isAnalyzing: mutation.isPending,
      analysisError: mutation.error?.message ?? null,
      runAnalysis,
      retryAnalysis: () => {
        if (lastRun) runAnalysis(lastRun.input, lastRun.prevScore)
      },
      reset: () => {
        resetMutation()
        setDraft(EMPTY_DRAFT)
        setAnalysis(null)
        setPrevScore(null)
        setSelection({})
      },
      selection,
      setSelection,
      chat,
      setChat,
    }
  }, [draft, analysis, prevScore, mutation.isPending, mutation.error, runAnalysis, lastRun, resetMutation, selection, chat])

  return <ApplicationContext.Provider value={value}>{children}</ApplicationContext.Provider>
}
