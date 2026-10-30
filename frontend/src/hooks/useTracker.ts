import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { NewTrackerEntry, Status } from '../api/types'

const TRACKER_KEY = ['tracker']

export const useTrackerEntries = () => useQuery({ queryKey: TRACKER_KEY, queryFn: api.tracker.list })

function useInvalidateTracker() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: TRACKER_KEY })
}

export function useAddTrackerEntry() {
  const onSuccess = useInvalidateTracker()
  return useMutation({ mutationFn: (entry: NewTrackerEntry) => api.tracker.add(entry), onSuccess })
}

export function useUpdateTrackerStatus() {
  const onSuccess = useInvalidateTracker()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: Status }) => api.tracker.updateStatus(id, status),
    onSuccess,
  })
}

export function useRemoveTrackerEntry() {
  const onSuccess = useInvalidateTracker()
  return useMutation({ mutationFn: (id: string) => api.tracker.remove(id), onSuccess })
}
