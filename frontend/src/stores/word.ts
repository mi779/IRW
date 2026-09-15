import { ref } from 'vue'
import { defineStore } from 'pinia'
import wordService from '@/services/wordService'
import type { Word } from '@/types'

export const useWordStore = defineStore('word', () => {
  const words = ref<Word[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(50)
  const search = ref('')
  const selectedWord = ref<Word | null>(null)
  const loading = ref(false)

  async function fetchPage(p = page.value, s = search.value) {
    loading.value = true
    try {
      const res = await wordService.getPage({
        search: s,
        skip: (p - 1) * pageSize.value,
        limit: pageSize.value,
      })
      words.value = res.items
      total.value = res.total
      page.value = p
      search.value = s
    } finally {
      loading.value = false
    }
  }

  async function fetchByRoot(rootId: number) {
    loading.value = true
    try {
      words.value = await wordService.getByRoot(rootId)
    } finally {
      loading.value = false
    }
  }

  async function fetchByPrefix(prefixId: number) {
    loading.value = true
    try {
      words.value = await wordService.getByPrefix(prefixId)
    } finally {
      loading.value = false
    }
  }

  async function fetchById(id: number) {
    selectedWord.value = await wordService.getById(id)
  }

  async function create(data: unknown) {
    await wordService.create(data)
    await fetchPage()
  }

  async function update(id: number, data: unknown) {
    await wordService.update(id, data)
    await fetchPage()
  }

  async function remove(id: number) {
    await wordService.delete(id)
    await fetchPage()
  }

  return {
    words,
    total,
    page,
    pageSize,
    search,
    selectedWord,
    loading,
    fetchPage,
    fetchByRoot,
    fetchByPrefix,
    fetchById,
    create,
    update,
    remove,
  }
})
