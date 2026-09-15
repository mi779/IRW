<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useReviewStore } from '@/stores/review'
import { useWordStore } from '@/stores/word'
import ReviewPanel from '@/components/ReviewPanel.vue'

const reviewStore = useReviewStore()
const wordStore = useWordStore()

const isFinished = computed(
  () => reviewStore.reviewQueue.length > 0 && reviewStore.currentIndex >= reviewStore.reviewQueue.length,
)

const currentItem = computed(() => reviewStore.currentItem)

onMounted(async () => {
  await reviewStore.fetchQueue()
  await loadCurrentWord()
})

async function loadCurrentWord() {
  if (currentItem.value) {
    await wordStore.fetchById(currentItem.value.word_id)
  }
}

async function handleRate(quality: number) {
  await reviewStore.logReview(quality)
  if (reviewStore.currentWord) {
    // load next word's detail
    if (reviewStore.currentItem) {
      await wordStore.fetchById(reviewStore.currentItem.word_id)
    }
  }
  if (isFinished.value) {
    ElMessage.success('今日复习已完成')
  }
}

const progressText = computed(() => {
  if (reviewStore.total === 0) return '0 / 0'
  return `${Math.min(reviewStore.currentIndex + 1, reviewStore.total)} / ${reviewStore.total}`
})
</script>

<template>
  <div class="review-view">
    <h2>复习</h2>
    <div v-if="reviewStore.loading" class="loading-text">加载中…</div>
    <div v-else-if="reviewStore.total === 0" class="empty-state">
      <el-empty description="今日复习已完成" />
    </div>
    <div v-else-if="isFinished" class="empty-state">
      <el-empty description="今日复习已完成" />
    </div>
    <div v-else class="review-content">
      <div class="progress-bar">
        <span class="progress-text">进度：{{ progressText }}</span>
        <el-progress
          :percentage="Math.round(reviewStore.progress * 100)"
          :stroke-width="10"
        />
      </div>
      <div v-if="currentItem" class="current-info">
        <div class="spelling">{{ currentItem.spelling }}</div>
      </div>
      <ReviewPanel
        v-if="wordStore.selectedWord"
        :word="wordStore.selectedWord"
        @rate="handleRate"
      />
    </div>
  </div>
</template>

<style scoped>
.review-view {
  padding: 8px 0;
}

.review-view h2 {
  font-size: 22px;
  color: #303133;
  margin: 0 0 20px 0;
}

.loading-text,
.empty-state {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}

.review-content {
  max-width: 720px;
  margin: 0 auto;
}

.progress-bar {
  margin-bottom: 24px;
}

.progress-text {
  display: block;
  margin-bottom: 8px;
  color: #606266;
  font-size: 14px;
}

.current-info {
  text-align: center;
  margin-bottom: 16px;
}

.spelling {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}
</style>
