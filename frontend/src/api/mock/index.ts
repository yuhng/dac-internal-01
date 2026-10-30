import { ApiError, type ApiClient } from '../types'
import { reply } from './chat'
import { buildChanges } from './improvement'
import { analyze } from './scoring'
import { trackerStore } from './tracker'

const MAX_UPLOAD_BYTES = 300_000
const ANALYZE_DELAY_MS = 1400
const CHAT_DELAY_MS = 650

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function extractText(file: File) {
  if (!/\.txt$/i.test(file.name) && file.type !== 'text/plain') {
    throw new ApiError(`${file.name} can't be read in this demo. PDF and DOCX parsing needs a server-side parser. Paste the text instead, or upload a .txt file.`)
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new ApiError('That file is larger than 300 KB. Please upload a plain-text CV under 300 KB.')
  }
  try {
    return await file.text()
  } catch {
    throw new ApiError('The file could not be read. Try pasting the text instead.')
  }
}

export const mockApi: ApiClient = {
  documents: { extractText },
  scoring: {
    async analyze(input) {
      await sleep(ANALYZE_DELAY_MS)
      return analyze(input)
    },
  },
  improvement: {
    suggest: async analysis => buildChanges(analysis),
  },
  chat: {
    async send({ message, analysis }) {
      await sleep(CHAT_DELAY_MS)
      return reply(message, analysis)
    },
  },
  tracker: {
    list: async () => trackerStore.list(),
    add: async entry => trackerStore.add(entry),
    updateStatus: async (id, status) => trackerStore.updateStatus(id, status),
    remove: async id => trackerStore.remove(id),
  },
}
