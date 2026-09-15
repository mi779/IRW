import request from './request'
import type { Word } from '@/types'

export default {
  getAll: () => request.get<unknown, Word[]>('/words'),
  getById: (id: number) => request.get<unknown, Word>(`/words/${id}`),
  getByRoot: (rootId: number) => request.get<unknown, Word[]>(`/words/by-root/${rootId}`),
  getByPrefix: (prefixId: number) =>
    request.get<unknown, Word[]>(`/words/by-prefix/${prefixId}`),
  create: (data: unknown) => request.post<unknown, Word>('/words', data),
  update: (id: number, data: unknown) => request.put<unknown, Word>(`/words/${id}`, data),
  delete: (id: number) => request.delete(`/words/${id}`),
}
