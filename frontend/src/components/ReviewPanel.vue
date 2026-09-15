<script setup lang="ts">
import type { Word } from '@/types'
import WordCard from './WordCard.vue'

defineProps<{ word: Word }>()

const emit = defineEmits<{ (e: 'rate', quality: number): void }>()

const ratings: { quality: number; label: string; type: '' | 'success' | 'warning' | 'danger' }[] = [
  { quality: 0, label: '完全不会', type: 'danger' },
  { quality: 1, label: '不会', type: 'danger' },
  { quality: 2, label: '勉强', type: 'warning' },
  { quality: 3, label: '正确但费力', type: 'warning' },
  { quality: 4, label: '正确', type: 'success' },
  { quality: 5, label: '轻松', type: 'success' },
]
</script>

<template>
  <div class="review-panel">
    <WordCard :word="word" />
    <div class="rating-section">
      <div class="rating-title">你对这个单词的掌握程度？</div>
      <el-button-group class="rating-buttons">
        <el-button
          v-for="r in ratings"
          :key="r.quality"
          :type="r.type"
          @click="emit('rate', r.quality)"
        >
          {{ r.quality }} - {{ r.label }}
        </el-button>
      </el-button-group>
    </div>
  </div>
</template>

<style scoped>
.review-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.rating-section {
  text-align: center;
}

.rating-title {
  font-size: 16px;
  color: #303133;
  margin-bottom: 12px;
}

.rating-buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
