import { ref } from 'vue'
import { defineStore } from 'pinia'
import wordService from '@/services/wordService'
import type { Word } from '@/types'

export const useDictStore = defineStore('dict', () => {
  const words = ref<Word[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(50)
  const search = ref('')
  const loading = ref(false)

  async function fetchPage(p = page.value, size = pageSize.value, s = search.value) {
    loading.value = true
    try {
      const res = await wordService.getPage({
        search: s,
        skip: (p - 1) * size,
        limit: size,
      })
      words.value = res.items
      total.value = res.total
      page.value = p
      pageSize.value = size
      search.value = s
    } finally {
      loading.value = false
    }
  }

  return { words, total, page, pageSize, search, loading, fetchPage }
})
