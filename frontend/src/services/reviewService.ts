import request from './request'
import type { ReviewQueueItem, Word } from '@/types'

export default {
  getQueue: () => request.get<unknown, ReviewQueueItem[]>('/review/queue'),
  logReview: (wordId: number, quality: number) =>
    request.post<unknown, Word>('/review/log', { word_id: wordId, quality }),
}
