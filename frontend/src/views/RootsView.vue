<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMorphemeStore } from '@/stores/morpheme'
import { useWordStore } from '@/stores/word'
import type { Morpheme, Word } from '@/types'
import RootGraph from '@/components/RootGraph.vue'
import WordCard from '@/components/WordCard.vue'
const morphemeStore = useMorphemeStore()
const wordStore = useWordStore()
const searchKeyword = ref('')
const selectedRootId = ref<number | null>(null)
const selectedRoot = ref<Morpheme | null>(null)
const drawerVisible = ref(false)

// 右侧展示模式：overview = 词表总览（默认），graph = 思维导图
const viewMode = ref<'overview' | 'graph'>('overview')

// 总览：分页 + 单词搜索
const wordSearch = ref('')
const page = ref(1)
const pageSize = ref(50)

// 导图：展示词数上限（按词频取 Top N）
const graphLimit = ref(60)
const graphLoadedFor = ref<number | null>(null)

const filteredRoots = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return morphemeStore.roots
  return morphemeStore.roots.filter((r) => r.text.toLowerCase().includes(keyword) || (r.meaning?.toLowerCase().includes(keyword) ?? false))
})
const currentGraphData = computed(() => morphemeStore.graphData)
const rootWords = computed(() => morphemeStore.rootWords)
const totalWords = computed(() => rootWords.value?.total ?? selectedRoot.value?.word_count ?? 0)

onMounted(() => { morphemeStore.fetchRoots().catch(() => {}) })

const TAG_LABELS: Record<string, string> = {
  zk: '中考', gk: '高考', cet4: '四级', cet6: '六级', ky: '考研',
  toefl: '托福', ielts: '雅思', gre: 'GRE',
}
function tagLabel(tag: string) { return TAG_LABELS[tag] ?? tag }

function wordPhonetics(w: Word) { return w.phonetics?.uk || w.phonetics?.us || '' }
function wordDefinition(w: Word) {
  const d = w.definitions?.[0]
  return d ? `${d.pos ? d.pos + ' ' : ''}${d.text}` : '—'
}
function wordTags(w: Word) { return (w.tags ?? []).slice(0, 3) }
function freqType(w: Word): 'high' | 'mid' | 'low' {
  const f = w.frq ?? 0
  if (f > 0 && f <= 5000) return 'high'
  if (f > 0 && f <= 20000) return 'mid'
  return 'low'
}

async function loadRootWords() {
  if (!selectedRootId.value) return
  await morphemeStore.fetchRootWords(selectedRootId.value, {
    skip: (page.value - 1) * pageSize.value,
    limit: pageSize.value,
    search: wordSearch.value.trim(),
  })
}

async function selectRoot(root: Morpheme) {
  selectedRootId.value = root.id
  selectedRoot.value = root
  page.value = 1
  wordSearch.value = ''
  viewMode.value = 'overview'
  await loadRootWords()
}

async function onSelectWord(wordId: number) { await wordStore.fetchById(wordId); if (wordStore.selectedWord) { drawerVisible.value = true } }

// 搜索防抖：300ms 后重置到第一页并拉取
let searchTimer: number | undefined
watch(wordSearch, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => { page.value = 1; loadRootWords() }, 300)
})

// 导图懒加载：切到导图页签时才请求该词根的图数据
async function ensureGraph() {
  if (!selectedRootId.value || graphLoadedFor.value === selectedRootId.value) return
  graphLoadedFor.value = selectedRootId.value
  await morphemeStore.fetchRootGraph(selectedRootId.value, graphLimit.value)
}
watch(viewMode, (mode) => { if (mode === 'graph') { ensureGraph() } })
async function onGraphLimitChange() {
  if (!selectedRootId.value) return
  await morphemeStore.fetchRootGraph(selectedRootId.value, graphLimit.value)
}

function onSizeChange() { page.value = 1; loadRootWords() }
onBeforeUnmount(() => { window.clearTimeout(searchTimer) })
</script>

<template>
  <div class="roots-view">
    <div class="page-header">
      <div class="header-left">
        <div class="page-icon">🌳</div>
        <div>
          <h2 class="page-title">词根分组学习</h2>
          <p class="page-desc">总览 + 思维导图 · 可视化学习同根单词</p>
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
        <template v-if="selectedRoot">
          <div class="root-hero">
            <div class="root-hero-main">
              <span class="root-hero-text">{{ selectedRoot.text }}</span>
              <span class="root-hero-meaning">{{ selectedRoot.meaning || '—' }}</span>
              <el-tag type="success" effect="plain" round>{{ totalWords }} 个关联词</el-tag>
            </div>
            <p v-if="selectedRoot.description" class="root-hero-desc">{{ selectedRoot.description }}</p>
          </div>
          <div class="mode-bar">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button value="overview">📋 词表总览</el-radio-button>
              <el-radio-button value="graph">🗺️ 思维导图</el-radio-button>
            </el-radio-group>
            <div v-if="viewMode === 'overview'" class="panel-search word-search">
              <span>🔍</span>
              <input v-model="wordSearch" type="text" placeholder="在本词根下搜索单词..." class="panel-search-input" />
            </div>
            <div v-else class="graph-limit">
              <span class="graph-limit-label">高频词</span>
              <el-select v-model="graphLimit" size="small" style="width: 92px" @change="onGraphLimitChange">
                <el-option :value="30" label="Top 30" />
                <el-option :value="60" label="Top 60" />
                <el-option :value="120" label="Top 120" />
                <el-option :value="200" label="Top 200" />
              </el-select>
            </div>
          </div>

          <div v-show="viewMode === 'overview'" class="overview-wrap">
            <el-table :data="rootWords?.items ?? []" v-loading="morphemeStore.rootWordsLoading" size="small" class="words-table" @row-click="(row: Word) => onSelectWord(row.id)">
              <el-table-column label="单词" width="180">
                <template #default="{ row }">
                  <div class="word-cell">
                    <span class="word-spelling">{{ row.spelling }}</span>
                    <span v-if="wordPhonetics(row)" class="word-phon">{{ wordPhonetics(row) }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="释义" min-width="220">
                <template #default="{ row }">
                  <span class="word-def">{{ wordDefinition(row) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="标签" width="150">
                <template #default="{ row }">
                  <el-tag v-for="t in wordTags(row)" :key="t" size="small" effect="plain" class="word-tag">{{ tagLabel(t) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="词频" width="90" align="right">
                <template #default="{ row }">
                  <span :class="['freq', `freq-${freqType(row)}`]">{{ row.frq || '—' }}</span>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-row">
              <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="rootWords?.total ?? 0" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" size="small" @current-change="loadRootWords" @size-change="onSizeChange" />
            </div>
          </div>

          <div v-show="viewMode === 'graph'" class="graph-wrapper">
            <div class="graph-hint">按词频展示最常用的 {{ graphLimit }} 个单词（共 {{ totalWords }} 个）· 点击单词节点查看详情</div>
            <RootGraph v-if="currentGraphData" :graph-data="currentGraphData" @select-word="onSelectWord" />
          </div>
        </template>
        <el-empty v-else description="请选择左侧词根查看关联单词" />
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

.root-hero { padding: 14px 16px 12px; background: rgba(255, 255, 255, 0.4); border-radius: var(--lg-radius-md); margin-bottom: 8px; flex-shrink: 0; }
.root-hero-main { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.root-hero-text { font-size: 24px; font-weight: 800; color: #78350f; background: #fde68a; padding: 2px 14px; border-radius: 12px; border: 2px solid #f59e0b; }
.root-hero-meaning { font-size: 15px; font-weight: 600; color: var(--lg-text-primary); }
.root-hero-desc { margin: 8px 0 0; font-size: 12.5px; line-height: 1.6; color: var(--lg-text-tertiary); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; white-space: pre-line; }
.mode-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 12px; background: rgba(255, 255, 255, 0.4); border-radius: var(--lg-radius-md); margin-bottom: 8px; flex-shrink: 0; flex-wrap: wrap; }
.word-search .panel-search-input { width: 180px; }
.graph-limit { display: flex; align-items: center; gap: 8px; }
.graph-limit-label { font-size: 12px; color: var(--lg-text-tertiary); }
.overview-wrap { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.words-table { flex: 1; }
.words-table :deep(tbody tr) { cursor: pointer; }
.word-cell { display: flex; flex-direction: column; gap: 1px; }
.word-spelling { font-size: 14px; font-weight: 700; color: #1e1b4b; }
.word-phon { font-size: 11.5px; color: var(--lg-text-tertiary); }
.word-def { font-size: 12.5px; color: var(--lg-text-primary); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.word-tag { margin-right: 4px; }
.freq { font-size: 12.5px; font-variant-numeric: tabular-nums; }
.freq-high { color: #dc2626; font-weight: 700; }
.freq-mid { color: #d97706; font-weight: 600; }
.freq-low { color: var(--lg-text-tertiary); }
.pagination-row { display: flex; justify-content: flex-end; padding: 10px 4px 2px; flex-shrink: 0; }
.graph-hint { font-size: 12px; color: var(--lg-text-tertiary); padding: 6px 10px; background: rgba(99, 102, 241, 0.06); border-radius: var(--lg-radius-md); margin-bottom: 8px; }
</style>
