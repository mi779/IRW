import request from './request'
import type { Morpheme, GraphData, WordPage } from '@/types'

export default {
  // Roots
  getRoots: () => request.get<unknown, Morpheme[]>('/roots'),
  getRoot: (id: number) => request.get<unknown, Morpheme>(`/roots/${id}`),
  createRoot: (data: unknown) => request.post<unknown, Morpheme>('/roots', data),
  updateRoot: (id: number, data: unknown) =>
    request.put<unknown, Morpheme>(`/roots/${id}`, data),
  deleteRoot: (id: number) => request.delete(`/roots/${id}`),

  // Prefixes
  getPrefixes: () => request.get<unknown, Morpheme[]>('/prefixes'),
  getPrefix: (id: number) => request.get<unknown, Morpheme>(`/prefixes/${id}`),
  createPrefix: (data: unknown) => request.post<unknown, Morpheme>('/prefixes', data),
  updatePrefix: (id: number, data: unknown) =>
    request.put<unknown, Morpheme>(`/prefixes/${id}`, data),
  deletePrefix: (id: number) => request.delete(`/prefixes/${id}`),

  // Suffixes
  getSuffixes: () => request.get<unknown, Morpheme[]>('/suffixes'),
  getSuffix: (id: number) => request.get<unknown, Morpheme>(`/suffixes/${id}`),
  createSuffix: (data: unknown) => request.post<unknown, Morpheme>('/suffixes', data),
  updateSuffix: (id: number, data: unknown) =>
    request.put<unknown, Morpheme>(`/suffixes/${id}`, data),
  deleteSuffix: (id: number) => request.delete(`/suffixes/${id}`),

  // Graph
  getRootGraph: (id: number, limit = 60) =>
    request.get<unknown, GraphData>(`/graph/root/${id}`, { params: { limit } }),
  getPrefixGraph: (id: number) => request.get<unknown, GraphData>(`/graph/prefix/${id}`),
  getSuffixGraph: (id: number) => request.get<unknown, GraphData>(`/graph/suffix/${id}`),

  // Paginated words linked to a root (most frequent first)
  getRootWords: (
    rootId: number,
    params: { skip?: number; limit?: number; search?: string },
  ) => request.get<unknown, WordPage>(`/words/by-root/${rootId}`, { params }),
}
