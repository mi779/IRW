import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import reviewService from '@/services/reviewService'
import type { ReviewQueueItem, Word } from '@/types'

export const useReviewStore = defineStore('review', () => {
  const reviewQueue = ref<ReviewQueueItem[]>([])
  const currentIndex = ref(0)
  const currentWord = ref<Word | null>(null)
  const loading = ref(false)

  const total = computed(() => reviewQueue.value.length)
  const remaining = computed(() => reviewQueue.value.length - currentIndex.value)
  const currentItem = computed<ReviewQueueItem | null>(() =>
    currentIndex.value < reviewQueue.value.length
      ? reviewQueue.value[currentIndex.value]!
      : null,
  )
  const progress = computed(() =>
    total.value === 0 ? 0 : currentIndex.value / total.value,
  )

  async function fetchQueue() {
    loading.value = true
    try {
      reviewQueue.value = await reviewService.getQueue()
      currentIndex.value = 0
      currentWord.value = null
    } finally {
      loading.value = false
    }
  }

  async function logReview(quality: number) {
    if (!currentItem.value) return
    const wordId = currentItem.value.word_id
    loading.value = true
    try {
      currentWord.value = await reviewService.logReview(wordId, quality)
      currentIndex.value++
    } finally {
      loading.value = false
    }
  }

  return {
    reviewQueue,
    currentIndex,
    currentWord,
    loading,
    total,
    remaining,
    currentItem,
    progress,
    fetchQueue,
    logReview,
  }
})
