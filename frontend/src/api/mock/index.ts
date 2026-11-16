import type { ApiClient } from '../types'
import { reply } from './chat'
import { buildChanges } from './improvement'
import { trackerStore } from './tracker'

const CHAT_DELAY_MS = 650

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/** Modules that have no backend endpoint yet. Documents and scoring always use FastAPI (see client.ts). */
export const mockApi: Omit<ApiClient, 'documents' | 'scoring'> = {
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
