import request from './request'
import type { Word, WordPage, WordRelated } from '@/types'

export interface WordPageParams {
  search?: string
  skip?: number
  limit?: number
}

export default {
  getPage: (params: WordPageParams) =>
    request.get<unknown, WordPage>('/words', { params }),
  getById: (id: number) => request.get<unknown, Word>(`/words/${id}`),
  getRelated: (id: number) => request.get<unknown, WordRelated>(`/words/${id}/related`),
  getByRoot: (rootId: number) => request.get<unknown, Word[]>(`/words/by-root/${rootId}`),
  getByPrefix: (prefixId: number) =>
    request.get<unknown, Word[]>(`/words/by-prefix/${prefixId}`),
  create: (data: unknown) => request.post<unknown, Word>('/words', data),
  update: (id: number, data: unknown) => request.put<unknown, Word>(`/words/${id}`, data),
  delete: (id: number) => request.delete(`/words/${id}`),
}
