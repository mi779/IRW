<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDictStore } from '@/stores/dict'
import type { Word } from '@/types'

const dictStore = useDictStore()
const searchInput = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  dictStore.fetchPage(1).catch(() => {})
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})

watch(searchInput, (val) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    dictStore.fetchPage(1, dictStore.pageSize, val.trim()).catch(() => {})
  }, 300)
})

function handleSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  dictStore.fetchPage(1, dictStore.pageSize, searchInput.value.trim()).catch(() => {})
}

function handlePageChange(p: number) {
  dictStore.fetchPage(p).catch(() => {})
}

function handleSizeChange(size: number) {
  dictStore.fetchPage(1, size).catch(() => {})
}

function phoneticUk(w: Word): string {
  return w.phonetics?.uk || ''
}

function phoneticUs(w: Word): string {
  return w.phonetics?.us || ''
}

function formatDefinitions(w: Word): string {
  if (!w.definitions?.length) return ''
  return w.definitions.map((d) => (d.pos ? d.pos + ' ' : '') + d.text).join('；')
}

function hasPhonetics(w: Word): boolean {
  return Boolean(w.phonetics?.uk || w.phonetics?.us)
}
</script>

<template>
  <div class="dict-words-view">
    <div class="page-header">
      <div class="header-left">
        <div class="page-icon">📖</div>
        <div>
          <h2 class="page-title">单词管理</h2>
          <p class="page-desc">欧路词典词库 · 共 {{ dictStore.total.toLocaleString() }} 词</p>
        </div>
      </div>
      <div class="header-actions">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchInput"
            type="text"
            placeholder="模糊搜索单词，如 spec ..."
            class="search-input"
            @keyup.enter="handleSearch"
          />
          <button v-if="searchInput" class="search-clear" @click="searchInput = ''">✕</button>
          <button class="search-btn" @click="handleSearch">搜索</button>
        </div>
      </div>
    </div>

    <div class="table-card lg-glass">
      <el-table :data="dictStore.words" v-loading="dictStore.loading" border stripe>
        <el-table-column prop="spelling" label="单词" width="170" fixed>
          <template #default="{ row }">
            <span class="word-spelling">{{ row.spelling }}</span>
          </template>
        </el-table-column>
        <el-table-column label="音标" width="210">
          <template #default="{ row }">
            <div v-if="hasPhonetics(row)" class="phonetic-block">
              <div v-if="phoneticUk(row)"><span class="ph-tag">uk</span> {{ phoneticUk(row) }}</div>
              <div v-if="phoneticUs(row)"><span class="ph-tag">us</span> {{ phoneticUs(row) }}</div>
            </div>
            <span v-else class="empty-cell">-</span>
          </template>
        </el-table-column>
        <el-table-column label="中文含义" min-width="300">
          <template #default="{ row }">
            <span v-if="formatDefinitions(row)" class="definition-text">{{ formatDefinitions(row) }}</span>
            <span v-else class="empty-cell">-</span>
          </template>
        </el-table-column>
        <el-table-column label="中文音译" width="150">
          <template #default="{ row }">
            <span v-if="row.transliteration" class="translit-chip">{{ row.transliteration }}</span>
            <span v-else class="empty-cell">-</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-empty-hint" v-if="!dictStore.loading && !dictStore.words.length">
        没有匹配的单词
      </div>
      <div class="pagination-bar">
        <el-pagination
          :total="dictStore.total"
          :current-page="dictStore.page"
          :page-size="dictStore.pageSize"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.dict-words-view { padding: 8px 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 20px; flex-wrap: wrap; }
.header-left { display: flex; align-items: center; gap: 14px; }
.page-icon { width: 48px; height: 48px; border-radius: 16px; background: var(--lg-gradient-primary); display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3); }
.page-title { margin: 0; font-size: 22px; font-weight: 700; color: var(--lg-text-primary); }
.page-desc { margin: 2px 0 0; font-size: 13px; color: var(--lg-text-tertiary); }
.header-actions { display: flex; align-items: center; gap: 12px; }
.search-box { display: flex; align-items: center; gap: 6px; padding: 4px 4px 4px 14px; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(99, 102, 241, 0.1); border-radius: var(--lg-radius-pill); transition: all 0.3s ease; min-width: 320px; }
.search-box:focus-within { border-color: rgba(99, 102, 241, 0.3); background: rgba(255, 255, 255, 0.9); box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.08); }
.search-icon { font-size: 14px; }
.search-input { flex: 1; border: none; background: transparent; outline: none; font-size: 14px; color: var(--lg-text-primary); padding: 6px 0; font-family: inherit; }
.search-input::placeholder { color: var(--lg-text-tertiary); }
.search-clear { width: 22px; height: 22px; border-radius: 50%; border: none; background: rgba(99, 102, 241, 0.1); color: var(--lg-text-secondary); font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.search-btn { padding: 8px 18px; border: none; border-radius: var(--lg-radius-pill); background: var(--lg-gradient-primary); color: white; font-size: 13px; font-weight: 600; font-family: inherit; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3); }
.search-btn:hover { box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4); }
.table-card { padding: 8px; border-radius: var(--lg-radius-xl); }
.word-spelling { font-weight: 700; color: var(--lg-primary, #6366f1); font-size: 14.5px; }
.phonetic-block { font-size: 12.5px; color: var(--lg-text-secondary); line-height: 1.6; }
.ph-tag { display: inline-block; font-size: 10px; color: #fff; background: rgba(99, 102, 241, 0.55); border-radius: 4px; padding: 0 4px; margin-right: 4px; vertical-align: 1px; }
.definition-text { font-size: 13px; color: var(--lg-text-primary); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.translit-chip { display: inline-block; font-size: 12.5px; color: #7c3aed; background: rgba(124, 58, 237, 0.08); border: 1px solid rgba(124, 58, 237, 0.18); border-radius: var(--lg-radius-pill, 999px); padding: 2px 10px; white-space: nowrap; }
.empty-cell { color: var(--lg-text-tertiary); opacity: 0.5; }
.table-empty-hint { text-align: center; padding: 28px 0 10px; font-size: 13.5px; color: var(--lg-text-tertiary); }
.pagination-bar { display: flex; justify-content: flex-end; margin-top: 16px; padding: 4px 8px; }
</style>
