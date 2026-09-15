<script setup lang="ts">
import type { Word } from '@/types'
import WordCard from './WordCard.vue'
defineProps<{ word: Word }>()
const emit = defineEmits<{ (e: 'rate', quality: number): void }>()
const ratings = [
  { quality: 0, label: '完全不会', gradient: 'linear-gradient(135deg, #ef4444, #dc2626)' },
  { quality: 1, label: '不会', gradient: 'linear-gradient(135deg, #f97316, #ea580c)' },
  { quality: 2, label: '勉强', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' },
  { quality: 3, label: '正确但费力', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
  { quality: 4, label: '正确', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  { quality: 5, label: '轻松', gradient: 'linear-gradient(135deg, #22d3ee, #06b6d4)' },
]
</script>

<template>
  <div class="review-panel">
    <WordCard :word="word" />
    <div class="rating-section lg-glass">
      <div class="rating-title"><span class="title-bar"></span>你对这个单词的掌握程度？</div>
      <div class="rating-buttons">
        <button v-for="r in ratings" :key="r.quality" class="rating-btn" :style="{ '--btn-gradient': r.gradient }" @click="emit('rate', r.quality)">
          <span class="btn-num">{{ r.quality }}</span>
          <span class="btn-label">{{ r.label }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.review-panel { display: flex; flex-direction: column; gap: 20px; }
.rating-section { padding: 24px; border-radius: var(--lg-radius-xl); }
.rating-title { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: var(--lg-text-primary); margin-bottom: 18px; justify-content: center; }
.title-bar { width: 3px; height: 14px; border-radius: 2px; background: var(--lg-gradient-primary); }
.rating-buttons { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
@media (max-width: 500px) { .rating-buttons { grid-template-columns: repeat(2, 1fr); } }
.rating-btn { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 14px 10px; border: none; border-radius: var(--lg-radius-md); background: rgba(255, 255, 255, 0.5); border: 1px solid rgba(99, 102, 241, 0.1); cursor: pointer; font-family: inherit; transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); position: relative; overflow: hidden; }
.rating-btn::before { content: ''; position: absolute; inset: 0; background: var(--btn-gradient); opacity: 0; transition: opacity 0.3s ease; }
.rating-btn:hover { transform: translateY(-2px); border-color: transparent; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1); }
.rating-btn:hover::before { opacity: 1; }
.rating-btn:hover .btn-num, .rating-btn:hover .btn-label { color: white; }
.btn-num { position: relative; font-size: 20px; font-weight: 700; color: var(--lg-text-primary); transition: color 0.3s ease; }
.btn-label { position: relative; font-size: 12px; font-weight: 500; color: var(--lg-text-secondary); transition: color 0.3s ease; }
</style>
