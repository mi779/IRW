<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWordStore } from '@/stores/word'
import type { Word } from '@/types'
import WordForm from '@/components/WordForm.vue'
const wordStore = useWordStore()
const dialogVisible = ref(false)
const editingWord = ref<Word | null>(null)
const searchInput = ref('')
onMounted(() => { wordStore.fetchPage(1).catch(() => {}) })
function openCreate() { editingWord.value = null; dialogVisible.value = true }
function openEdit(row: Word) { editingWord.value = row; dialogVisible.value = true }
async function handleDelete(row: Word) {
  try { await ElMessageBox.confirm('确认删除单词「' + row.spelling + '」？', '提示', { type: 'warning' }); await wordStore.remove(row.id); ElMessage.success('删除成功') } catch {}
}
function handleSearch() { wordStore.fetchPage(1, searchInput.value).catch(() => {}) }
function handlePageChange(p: number) { wordStore.fetchPage(p).catch(() => {}) }
function formatDefinitions(word: Word): string { if (!word.definitions?.length) return '-'; return word.definitions.map((d) => d.pos + ' ' + d.text).join('；') }
function formatPhonetics(word: Word): string { if (!word.phonetics) return '-'; return Object.entries(word.phonetics).map(([k, v]) => k + ':' + v).join('  ') }
function formatRoots(word: Word): string { if (!word.roots?.length) return '-'; return word.roots.map((r) => r.text).join('，') }
</script>

<template>
  <div class="words-view">
    <div class="page-header">
      <div class="header-left">
        <div class="page-icon">📚</div>
        <div>
          <h2 class="page-title">单词管理</h2>
          <p class="page-desc">管理你的词汇库</p>
        </div>
      </div>
      <div class="header-actions">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input v-model="searchInput" type="text" placeholder="搜索单词拼写..." class="search-input" @keyup.enter="handleSearch" />
          <button v-if="searchInput" class="search-clear" @click="searchInput = ''; handleSearch()">✕</button>
          <button class="search-btn" @click="handleSearch">搜索</button>
        </div>
        <button class="btn-add" @click="openCreate">+ 添加单词</button>
      </div>
    </div>
    <div class="table-card lg-glass">
      <el-table :data="wordStore.words" v-loading="wordStore.loading" border stripe>
        <el-table-column prop="spelling" label="拼写" width="160" />
        <el-table-column label="音标" width="220"><template #default="{ row }">{{ formatPhonetics(row) }}</template></el-table-column>
        <el-table-column label="释义" min-width="240"><template #default="{ row }">{{ formatDefinitions(row) }}</template></el-table-column>
        <el-table-column label="词根" width="140"><template #default="{ row }">{{ formatRoots(row) }}</template></el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination :total="wordStore.total" :current-page="wordStore.page" :page-size="wordStore.pageSize" layout="total, prev, pager, next, jumper" background @current-change="handlePageChange" />
      </div>
    </div>
    <WordForm v-model="dialogVisible" :word="editingWord" />
  </div>
</template>

<style scoped>
.words-view { padding: 8px 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 20px; flex-wrap: wrap; }
.header-left { display: flex; align-items: center; gap: 14px; }
.page-icon { width: 48px; height: 48px; border-radius: 16px; background: var(--lg-gradient-primary); display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3); }
.page-title { margin: 0; font-size: 22px; font-weight: 700; color: var(--lg-text-primary); }
.page-desc { margin: 2px 0 0; font-size: 13px; color: var(--lg-text-tertiary); }
.header-actions { display: flex; align-items: center; gap: 12px; }
.search-box { display: flex; align-items: center; gap: 6px; padding: 4px 4px 4px 14px; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(99, 102, 241, 0.1); border-radius: var(--lg-radius-pill); transition: all 0.3s ease; min-width: 300px; }
.search-box:focus-within { border-color: rgba(99, 102, 241, 0.3); background: rgba(255, 255, 255, 0.9); box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.08); }
.search-icon { font-size: 14px; }
.search-input { flex: 1; border: none; background: transparent; outline: none; font-size: 14px; color: var(--lg-text-primary); padding: 6px 0; font-family: inherit; }
.search-input::placeholder { color: var(--lg-text-tertiary); }
.search-clear { width: 22px; height: 22px; border-radius: 50%; border: none; background: rgba(99, 102, 241, 0.1); color: var(--lg-text-secondary); font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.search-btn { padding: 8px 18px; border: none; border-radius: var(--lg-radius-pill); background: var(--lg-gradient-primary); color: white; font-size: 13px; font-weight: 600; font-family: inherit; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3); }
.search-btn:hover { box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4); }
.btn-add { display: inline-flex; align-items: center; gap: 6px; padding: 10px 22px; border: none; border-radius: var(--lg-radius-pill); background: var(--lg-gradient-primary); color: white; font-size: 14px; font-weight: 600; font-family: inherit; cursor: pointer; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.btn-add:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45); }
.table-card { padding: 8px; border-radius: var(--lg-radius-xl); }
.pagination-bar { display: flex; justify-content: flex-end; margin-top: 16px; padding: 4px 8px; }
</style>
