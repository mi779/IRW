import { ref } from 'vue'
import { defineStore } from 'pinia'
import morphemeService from '@/services/morphemeService'
import type { Morpheme, GraphData, WordPage } from '@/types'

export const useMorphemeStore = defineStore('morpheme', () => {
  const roots = ref<Morpheme[]>([])
  const prefixes = ref<Morpheme[]>([])
  const suffixes = ref<Morpheme[]>([])
  const graphData = ref<GraphData | null>(null)
  const rootWords = ref<WordPage | null>(null)
  const rootWordsLoading = ref(false)
  const loading = ref(false)

  async function fetchRoots() {
    loading.value = true
    try {
      roots.value = await morphemeService.getRoots()
    } finally {
      loading.value = false
    }
  }

  async function createRoot(data: unknown) {
    await morphemeService.createRoot(data)
    await fetchRoots()
  }

  async function updateRoot(id: number, data: unknown) {
    await morphemeService.updateRoot(id, data)
    await fetchRoots()
  }

  async function deleteRoot(id: number) {
    await morphemeService.deleteRoot(id)
    await fetchRoots()
  }

  async function fetchPrefixes() {
    loading.value = true
    try {
      prefixes.value = await morphemeService.getPrefixes()
    } finally {
      loading.value = false
    }
  }

  async function createPrefix(data: unknown) {
    await morphemeService.createPrefix(data)
    await fetchPrefixes()
  }

  async function updatePrefix(id: number, data: unknown) {
    await morphemeService.updatePrefix(id, data)
    await fetchPrefixes()
  }

  async function deletePrefix(id: number) {
    await morphemeService.deletePrefix(id)
    await fetchPrefixes()
  }

  async function fetchSuffixes() {
    loading.value = true
    try {
      suffixes.value = await morphemeService.getSuffixes()
    } finally {
      loading.value = false
    }
  }

  async function createSuffix(data: unknown) {
    await morphemeService.createSuffix(data)
    await fetchSuffixes()
  }

  async function updateSuffix(id: number, data: unknown) {
    await morphemeService.updateSuffix(id, data)
    await fetchSuffixes()
  }

  async function deleteSuffix(id: number) {
    await morphemeService.deleteSuffix(id)
    await fetchSuffixes()
  }

  async function fetchRootGraph(id: number, limit = 60) {
    loading.value = true
    try {
      graphData.value = await morphemeService.getRootGraph(id, limit)
    } finally {
      loading.value = false
    }
  }

  async function fetchRootWords(
    rootId: number,
    opts: { skip?: number; limit?: number; search?: string } = {},
  ) {
    rootWordsLoading.value = true
    try {
      rootWords.value = await morphemeService.getRootWords(rootId, opts)
    } finally {
      rootWordsLoading.value = false
    }
  }

  async function fetchPrefixGraph(id: number) {
    loading.value = true
    try {
      graphData.value = await morphemeService.getPrefixGraph(id)
    } finally {
      loading.value = false
    }
  }

  async function fetchSuffixGraph(id: number) {
    loading.value = true
    try {
      graphData.value = await morphemeService.getSuffixGraph(id)
    } finally {
      loading.value = false
    }
  }

  return {
    roots,
    prefixes,
    suffixes,
    graphData,
    rootWords,
    rootWordsLoading,
    loading,
    fetchRoots,
    createRoot,
    updateRoot,
    deleteRoot,
    fetchPrefixes,
    createPrefix,
    updatePrefix,
    deletePrefix,
    fetchSuffixes,
    createSuffix,
    updateSuffix,
    deleteSuffix,
    fetchRootGraph,
    fetchRootWords,
    fetchPrefixGraph,
    fetchSuffixGraph,
  }
})
