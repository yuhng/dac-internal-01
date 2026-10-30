import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { RichBlock } from '../api/types'
import { RichBlocks } from '../components/RichText'
import { PageHead, SimulatedBadge } from '../components/ui'
import { GREETING } from '../lib/greeting'
import { useApplication } from '../state/useApplication'

const SUGGESTIONS = [
  'Explain my score',
  'Which keywords am I missing?',
  'How can I improve my CV?',
  'Draft a cover letter opening',
  'Give me interview questions',
]

const BOT_BUBBLE = 'max-w-[92%] self-start rounded-[14px] rounded-bl bg-surface-2 px-3.5 py-2.5 text-sm sm:max-w-[78%]'

export function ChatPage() {
  const { analysis, chat, setChat } = useApplication()
  const [input, setInput] = useState('')
  const scroller = useRef<HTMLDivElement>(null)

  const send = useMutation({ mutationFn: api.chat.send })

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight })
  }, [chat, send.isPending])

  const submit = (raw: string) => {
    const message = raw.trim()
    if (!message || send.isPending) return
    setChat(messages => [...messages, { id: crypto.randomUUID(), from: 'user', text: message }])
    const addBotMessage = (blocks: RichBlock[]) =>
      setChat(messages => [...messages, { id: crypto.randomUUID(), from: 'bot', blocks }])
    send.mutate({ message, analysis }, {
      onSuccess: addBotMessage,
      onError: () => addBotMessage([{ kind: 'text', text: 'Sorry, something went wrong. Please try again.' }]),
    })
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setInput('')
    submit(input)
  }

  return (
    <>
      <PageHead
        title="Application Assistant"
        subtitle="Ask about your score, gaps, cover letter or interview prep."
        actions={<button type="button" className="btn" onClick={() => setChat(() => [])}>Clear conversation</button>}
      />
      <div className="card flex h-[calc(100vh-220px)] min-h-[460px] flex-col !p-0 md:h-[calc(100vh-190px)]">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3 text-[13px]">
          <span>
            {analysis
              ? <>Context: <b>{analysis.title || 'Untitled role'}</b>{analysis.company && ` at ${analysis.company}`} · score {analysis.overall}</>
              : <span className="text-muted">No analysis loaded. Answers will be generic.</span>}
          </span>
          <SimulatedBadge>Scripted responses</SimulatedBadge>
        </div>
        <div ref={scroller} aria-live="polite" className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-[18px]">
          <div className={BOT_BUBBLE}><RichBlocks blocks={GREETING} /></div>
          {chat.map(message => message.from === 'user'
            ? <div key={message.id} className="max-w-[92%] self-end rounded-[14px] rounded-br bg-primary px-3.5 py-2.5 text-sm whitespace-pre-wrap text-on-primary sm:max-w-[78%]">{message.text}</div>
            : <div key={message.id} className={BOT_BUBBLE}><RichBlocks blocks={message.blocks} /></div>)}
          {send.isPending && <div className={`${BOT_BUBBLE} text-muted italic`}>Assistant is typing…</div>}
        </div>
        <div className="flex flex-wrap gap-1.5 px-4 pb-2.5">
          {SUGGESTIONS.map(suggestion => (
            <button key={suggestion} type="button" className="cursor-pointer rounded-full border border-line px-[11px] py-[5px] text-[13px] text-primary hover:bg-primary-weak" onClick={() => submit(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
        <form className="flex gap-2 border-t border-line px-4 py-3" onSubmit={handleSubmit}>
          <input type="text" className="input" placeholder="Ask a question…" autoComplete="off" aria-label="Message" value={input} onChange={e => setInput(e.target.value)} />
          <button type="submit" className="btn btn-primary">Send</button>
        </form>
      </div>
    </>
  )
}
