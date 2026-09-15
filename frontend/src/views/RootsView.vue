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
  return morphemeStore.roots.filter(
    (r) =>
      r.text.toLowerCase().includes(keyword) ||
      (r.meaning?.toLowerCase().includes(keyword) ?? false),
  )
})

const currentGraphData = computed(() => morphemeStore.graphData)

onMounted(() => {
  morphemeStore.fetchRoots().catch(() => {})
})

async function selectRoot(root: Morpheme) {
  selectedRootId.value = root.id
  await morphemeStore.fetchRootGraph(root.id)
}

async function onSelectWord(wordId: number) {
  await wordStore.fetchById(wordId)
  if (wordStore.selectedWord) {
    drawerVisible.value = true
  }
}
</script>

<template>
  <div class="roots-view">
    <h2>词根分组学习</h2>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="never" class="left-panel">
          <template #header>
            <div class="panel-header">
              <span>词根列表</span>
              <el-input
                v-model="searchKeyword"
                placeholder="搜索词根"
                clearable
                size="small"
                class="search-input"
              />
            </div>
          </template>
          <el-table
            :data="filteredRoots"
            v-loading="morphemeStore.loading && !currentGraphData"
            highlight-current-row
            @row-click="selectRoot"
            size="small"
          >
            <el-table-column prop="text" label="词根" width="100" />
            <el-table-column prop="meaning" label="含义" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="never" class="right-panel">
          <template #header>
            <span>关系图</span>
          </template>
          <div v-if="currentGraphData" class="graph-wrapper">
            <RootGraph :graph-data="currentGraphData" @select-word="onSelectWord" />
            <div class="graph-tip">点击图中蓝色节点查看单词详情</div>
          </div>
          <el-empty v-else description="请选择左侧词根以查看关系图" />
        </el-card>
      </el-col>
    </el-row>

    <el-drawer v-model="drawerVisible" title="单词详情" size="480px">
      <WordCard v-if="wordStore.selectedWord" :word="wordStore.selectedWord" />
    </el-drawer>
  </div>
</template>

<style scoped>
.roots-view {
  padding: 8px 0;
}

.roots-view h2 {
  font-size: 22px;
  color: #303133;
  margin: 0 0 20px 0;
}

.left-panel,
.right-panel {
  height: 600px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.search-input {
  width: 180px;
}

.graph-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.graph-tip {
  color: #909399;
  font-size: 12px;
  text-align: center;
}
</style>
