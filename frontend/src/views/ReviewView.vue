<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useReviewStore } from '@/stores/review'
import { useWordStore } from '@/stores/word'
import ReviewPanel from '@/components/ReviewPanel.vue'
const reviewStore = useReviewStore()
const wordStore = useWordStore()
const isFinished = computed(() => reviewStore.reviewQueue.length > 0 && reviewStore.currentIndex >= reviewStore.reviewQueue.length)
const currentItem = computed(() => reviewStore.currentItem)
onMounted(async () => { await reviewStore.fetchQueue(); await loadCurrentWord() })
async function loadCurrentWord() { if (currentItem.value) { await wordStore.fetchById(currentItem.value.word_id) } }
async function handleRate(quality: number) {
  await reviewStore.logReview(quality)
  if (reviewStore.currentWord && reviewStore.currentItem) { await wordStore.fetchById(reviewStore.currentItem.word_id) }
  if (isFinished.value) { ElMessage.success('今日复习已完成') }
}
const progressText = computed(() => { if (reviewStore.total === 0) return '0 / 0'; return Math.min(reviewStore.currentIndex + 1, reviewStore.total) + ' / ' + reviewStore.total })
const progressPercent = computed(() => Math.round(reviewStore.progress * 100))
</script>

<template>
  <div class="review-view">
    <div class="page-header">
      <div class="header-left">
        <div class="page-icon">🎯</div>
        <div>
          <h2 class="page-title">复习</h2>
          <p class="page-desc">间隔重复 · 巩固长期记忆</p>
        </div>
      </div>
    </div>
    <div v-if="reviewStore.loading" class="state-card lg-glass">
      <div class="state-content"><div class="loader"></div><span>加载中...</span></div>
    </div>
    <div v-else-if="reviewStore.total === 0 || isFinished" class="state-card lg-glass">
      <div class="state-emoji">🎉</div>
      <h3 class="state-title">今日复习已完成</h3>
      <p class="state-desc">明天继续加油！</p>
    </div>
    <div v-else class="review-content">
      <div class="progress-card lg-glass">
        <div class="progress-info">
          <span class="progress-label">今日进度</span>
          <span class="progress-count">{{ progressText }}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" :style="{ width: progressPercent + '%' }"></div></div>
        <div class="progress-percent">{{ progressPercent }}%</div>
      </div>
      <div v-if="currentItem" class="spelling-card lg-glass">
        <div class="spelling">{{ currentItem.spelling }}</div>
      </div>
      <ReviewPanel v-if="wordStore.selectedWord" :word="wordStore.selectedWord" @rate="handleRate" />
    </div>
  </div>
</template>

<style scoped>
.review-view { padding: 8px 0; }
.page-header { display: flex; align-items: center; margin-bottom: 20px; }
.header-left { display: flex; align-items: center; gap: 14px; }
.page-icon { width: 48px; height: 48px; border-radius: 16px; background: linear-gradient(135deg, #10b981, #22d3ee); display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3); }
.page-title { font-size: 22px; font-weight: 700; color: var(--lg-text-primary); margin: 0; }
.page-desc { margin: 2px 0 0; font-size: 13px; color: var(--lg-text-tertiary); }
.state-card { text-align: center; padding: 56px 32px; max-width: 480px; margin: 40px auto; border-radius: var(--lg-radius-xl); }
.state-content { display: flex; flex-direction: column; align-items: center; gap: 16px; color: var(--lg-text-secondary); font-size: 15px; }
.state-emoji { font-size: 48px; margin-bottom: 8px; }
.state-title { font-size: 20px; font-weight: 600; color: var(--lg-text-primary); margin: 0 0 8px; }
.state-desc { font-size: 14px; color: var(--lg-text-tertiary); margin: 0; }
.loader { width: 32px; height: 32px; border: 3px solid rgba(99, 102, 241, 0.15); border-top-color: var(--lg-info); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.review-content { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
.progress-card { display: grid; grid-template-columns: auto 1fr auto; grid-template-rows: auto auto; gap: 8px 16px; align-items: center; padding: 20px 24px; border-radius: var(--lg-radius-lg); }
.progress-info { grid-column: 1; grid-row: 1; display: flex; flex-direction: column; }
.progress-label { font-size: 12px; color: var(--lg-text-tertiary); font-weight: 500; }
.progress-count { font-size: 18px; font-weight: 700; color: var(--lg-text-primary); }
.progress-track { grid-column: 2; grid-row: 1 / span 2; height: 10px; background: rgba(99, 102, 241, 0.1); border-radius: var(--lg-radius-pill); overflow: hidden; align-self: center; }
.progress-fill { height: 100%; background: var(--lg-gradient-primary); border-radius: var(--lg-radius-pill); transition: width 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); box-shadow: 0 0 12px rgba(99, 102, 241, 0.4); }
.progress-percent { grid-column: 3; grid-row: 1; font-size: 16px; font-weight: 700; color: var(--lg-info); }
.spelling-card { text-align: center; padding: 36px 24px; border-radius: var(--lg-radius-lg); }
.spelling { font-size: 36px; font-weight: 700; color: var(--lg-text-primary); letter-spacing: 0.02em; }
</style>
