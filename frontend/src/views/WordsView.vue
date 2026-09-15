<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWordStore } from '@/stores/word'
import type { Word } from '@/types'
import WordForm from '@/components/WordForm.vue'

const wordStore = useWordStore()

const dialogVisible = ref(false)
const editingWord = ref<Word | null>(null)

onMounted(() => {
  wordStore.fetchAll().catch(() => {})
})

function openCreate() {
  editingWord.value = null
  dialogVisible.value = true
}

function openEdit(row: Word) {
  editingWord.value = row
  dialogVisible.value = true
}

async function handleDelete(row: Word) {
  try {
    await ElMessageBox.confirm(`确认删除单词「${row.spelling}」？`, '提示', {
      type: 'warning',
    })
    await wordStore.remove(row.id)
    ElMessage.success('删除成功')
  } catch (err) {
    // canceled or failed
  }
}

function formatDefinitions(word: Word): string {
  if (!word.definitions?.length) return '-'
  return word.definitions.map((d) => `${d.pos} ${d.text}`).join('；')
}

function formatPhonetics(word: Word): string {
  if (!word.phonetics) return '-'
  return Object.entries(word.phonetics)
    .map(([k, v]) => `${k}:${v}`)
    .join('  ')
}

function formatRoots(word: Word): string {
  if (!word.roots?.length) return '-'
  return word.roots.map((r) => r.text).join('，')
}
</script>

<template>
  <div class="words-view">
    <div class="page-header">
      <h2>单词管理</h2>
      <el-button type="primary" @click="openCreate">+ 添加单词</el-button>
    </div>
    <el-table :data="wordStore.words" v-loading="wordStore.loading" border stripe>
      <el-table-column prop="spelling" label="拼写" width="160" />
      <el-table-column label="音标" width="220">
        <template #default="{ row }">{{ formatPhonetics(row) }}</template>
      </el-table-column>
      <el-table-column label="释义" min-width="240">
        <template #default="{ row }">{{ formatDefinitions(row) }}</template>
      </el-table-column>
      <el-table-column label="词根" width="140">
        <template #default="{ row }">{{ formatRoots(row) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <WordForm v-model="dialogVisible" :word="editingWord" />
  </div>
</template>

<style scoped>
.words-view {
  padding: 8px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
  color: #303133;
}
</style>
