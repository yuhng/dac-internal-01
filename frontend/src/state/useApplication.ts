import { createContext, useContext } from 'react'
import type { Analysis, RichBlock, ScoreInput } from '../api/types'

export type ChatMessage =
  | { id: string; from: 'user'; text: string }
  | { id: string; from: 'bot'; blocks: RichBlock[] }

export const trimInput = (input: ScoreInput): ScoreInput => ({
  title: input.title.trim(),
  company: input.company.trim(),
  jd: input.jd.trim(),
  cv: input.cv.trim(),
  cl: input.cl.trim(),
})

export interface ApplicationState {
  draft: ScoreInput
  updateDraft(patch: Partial<ScoreInput>): void
  analysis: Analysis | null
  /** Score of the previous CV version, set when re-scoring an improved CV. */
  prevScore: number | null
  stale: boolean
  isAnalyzing: boolean
  analysisError: string | null
  runAnalysis(input: ScoreInput, prevScore?: number | null): void
  retryAnalysis(): void
  reset(): void
  /** User overrides of which suggested edits are accepted, by change id. */
  selection: Record<string, boolean>
  setSelection(selection: Record<string, boolean>): void
  chat: ChatMessage[]
  setChat(update: (messages: ChatMessage[]) => ChatMessage[]): void
}

export const ApplicationContext = createContext<ApplicationState | null>(null)

export function useApplication() {
  const value = useContext(ApplicationContext)
  if (!value) throw new Error('useApplication must be used within ApplicationProvider')
  return value
}
