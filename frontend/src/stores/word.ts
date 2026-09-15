import { ref } from 'vue'
import { defineStore } from 'pinia'
import wordService from '@/services/wordService'
import type { Word } from '@/types'

export const useWordStore = defineStore('word', () => {
  const words = ref<Word[]>([])
  const selectedWord = ref<Word | null>(null)
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      words.value = await wordService.getAll()
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
    await fetchAll()
  }

  async function update(id: number, data: unknown) {
    await wordService.update(id, data)
    await fetchAll()
  }

  async function remove(id: number) {
    await wordService.delete(id)
    await fetchAll()
  }

  return {
    words,
    selectedWord,
    loading,
    fetchAll,
    fetchByRoot,
    fetchByPrefix,
    fetchById,
    create,
    update,
    remove,
  }
})
