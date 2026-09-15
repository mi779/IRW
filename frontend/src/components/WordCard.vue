<script setup lang="ts">
import type { Word } from '@/types'

defineProps<{ word: Word }>()
</script>

<template>
  <el-card class="word-card" shadow="hover">
    <div class="spelling">{{ word.spelling }}</div>
    <div v-if="word.phonetics" class="phonetics">
      <span v-for="(value, key) in word.phonetics" :key="key" class="phonetic-item">
        {{ key }}: {{ value }}
      </span>
    </div>
    <div v-if="word.definitions?.length" class="section">
      <div class="section-title">释义</div>
      <ul class="definitions">
        <li v-for="(def, idx) in word.definitions" :key="idx">
          <span class="pos">{{ def.pos }}</span>
          <span class="text">{{ def.text }}</span>
        </li>
      </ul>
    </div>
    <div v-if="word.example_sentences?.length" class="section">
      <div class="section-title">例句</div>
      <ul class="examples">
        <li v-for="(sentence, idx) in word.example_sentences" :key="idx">{{ sentence }}</li>
      </ul>
    </div>
    <div class="morphemes">
      <el-tag v-for="r in word.roots" :key="`r-${r.id}`" type="warning" class="morpheme-tag">
        词根 {{ r.text }}
      </el-tag>
      <el-tag v-for="p in word.prefixes" :key="`p-${p.id}`" type="success" class="morpheme-tag">
        前缀 {{ p.text }}
      </el-tag>
      <el-tag v-for="s in word.suffixes" :key="`s-${s.id}`" type="primary" class="morpheme-tag">
        后缀 {{ s.text }}
      </el-tag>
    </div>
  </el-card>
</template>

<style scoped>
.word-card {
  width: 100%;
}

.spelling {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.phonetics {
  color: #909399;
  font-size: 14px;
  margin-bottom: 12px;
}

.phonetic-item {
  margin-right: 16px;
}

.section {
  margin-top: 12px;
}

.section-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 6px;
  font-weight: 500;
}

.definitions,
.examples {
  margin: 0;
  padding-left: 20px;
}

.definitions li {
  margin-bottom: 4px;
}

.pos {
  display: inline-block;
  min-width: 40px;
  color: #e6a23c;
  font-style: italic;
  margin-right: 8px;
}

.morphemes {
  margin-top: 12px;
}

.morpheme-tag {
  margin-right: 6px;
  margin-bottom: 6px;
}
</style>
