<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useMorphemeStore } from '@/stores/morpheme'
import { useWordStore } from '@/stores/word'
import type { Morpheme } from '@/types'
import RootGraph from '@/components/RootGraph.vue'
import WordCard from '@/components/WordCard.vue'
const morphemeStore = useMorphemeStore()
const wordStore = useWordStore()
const searchKeyword = ref('')
const selectedRootId = ref<number | null>(null)
const drawerVisible = ref(false)
const filteredRoots = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return morphemeStore.roots
  return morphemeStore.roots.filter((r) => r.text.toLowerCase().includes(keyword) || (r.meaning?.toLowerCase().includes(keyword) ?? false))
})
const currentGraphData = computed(() => morphemeStore.graphData)
onMounted(() => { morphemeStore.fetchRoots().catch(() => {}) })
async function selectRoot(root: Morpheme) { selectedRootId.value = root.id; await morphemeStore.fetchRootGraph(root.id) }
async function onSelectWord(wordId: number) { await wordStore.fetchById(wordId); if (wordStore.selectedWord) { drawerVisible.value = true } }
</script>

<template>
  <div class="roots-view">
    <div class="page-header">
      <div class="header-left">
        <div class="page-icon">🌳</div>
        <div>
          <h2 class="page-title">词根分组学习</h2>
          <p class="page-desc">思维导图 · 可视化学习同根单词</p>
        </div>
      </div>
    </div>
    <div class="panels">
      <div class="left-panel lg-glass">
        <div class="panel-header">
          <span class="panel-title">词根列表</span>
          <div class="panel-search">
            <span>🔍</span>
            <input v-model="searchKeyword" type="text" placeholder="搜索词根..." class="panel-search-input" />
          </div>
        </div>
        <el-table :data="filteredRoots" v-loading="morphemeStore.loading && !currentGraphData" highlight-current-row @row-click="selectRoot" size="small" class="roots-table">
          <el-table-column prop="text" label="词根" width="100" />
          <el-table-column prop="meaning" label="含义" />
          <el-table-column label="词数" width="70" align="right"><template #default="{ row }">{{ row.word_count ?? 0 }}</template></el-table-column>
        </el-table>
      </div>
      <div class="right-panel lg-glass">
        <div class="panel-header">
          <span class="panel-title">思维导图</span>
          <span v-if="currentGraphData" class="panel-hint">点击单词节点查看详情</span>
        </div>
        <div v-if="currentGraphData" class="graph-wrapper">
          <RootGraph :graph-data="currentGraphData" @select-word="onSelectWord" />
        </div>
        <el-empty v-else description="请选择左侧词根以查看思维导图" />
      </div>
    </div>
    <el-drawer v-model="drawerVisible" title="单词详情" size="480px">
      <WordCard v-if="wordStore.selectedWord" :word="wordStore.selectedWord" />
    </el-drawer>
  </div>
</template>

<style scoped>
.roots-view { padding: 8px 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header-left { display: flex; align-items: center; gap: 14px; }
.page-icon { width: 48px; height: 48px; border-radius: 16px; background: linear-gradient(135deg, #2d6a4f, #40916c); display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 14px rgba(45, 106, 79, 0.3); }
.page-title { font-size: 22px; font-weight: 700; color: var(--lg-text-primary); margin: 0; }
.page-desc { margin: 2px 0 0; font-size: 13px; color: var(--lg-text-tertiary); }
.panels { display: grid; grid-template-columns: 320px 1fr; gap: 20px; }
@media (max-width: 900px) { .panels { grid-template-columns: 1fr; } }
.left-panel, .right-panel { display: flex; flex-direction: column; padding: 8px; border-radius: var(--lg-radius-xl); }
.left-panel { height: 600px; }
.right-panel { min-height: 600px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 16px; background: rgba(255, 255, 255, 0.4); border-radius: var(--lg-radius-md); margin-bottom: 8px; flex-shrink: 0; }
.panel-title { font-size: 15px; font-weight: 600; color: var(--lg-text-primary); }
.panel-hint { font-size: 12px; color: var(--lg-text-tertiary); }
.panel-search { display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: rgba(255, 255, 255, 0.6); border: 1px solid rgba(99, 102, 241, 0.08); border-radius: var(--lg-radius-pill); color: var(--lg-text-tertiary); transition: all 0.3s ease; }
.panel-search:focus-within { border-color: rgba(99, 102, 241, 0.25); background: rgba(255, 255, 255, 0.85); }
.panel-search-input { border: none; background: transparent; outline: none; font-size: 13px; color: var(--lg-text-primary); width: 140px; font-family: inherit; }
.panel-search-input::placeholder { color: var(--lg-text-tertiary); }
.roots-table { flex: 1; }
.graph-wrapper { flex: 1; overflow: auto; }
</style>
