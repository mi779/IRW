<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Graph } from '@antv/g6'
import type { GraphData } from '@/types'

const props = defineProps<{ graphData: GraphData }>()
const emit = defineEmits<{ (e: 'select-word', wordId: number): void }>()
const containerRef = ref<HTMLDivElement | null>(null)
let graph: Graph | null = null

// CJK characters are roughly twice as wide as latin letters at the same size.
function textWidth(s: string): number {
  return [...s].reduce((w, c) => w + (/[\u4e00-\u9fff]/.test(c) ? 14 : 8), 0)
}

function nodeSize(label: string, isWord: boolean): [number, number] {
  const w = textWidth(label) + (isWord ? 28 : 48)
  return [Math.max(isWord ? 72 : 96, w), isWord ? 30 : 44]
}

// Each mindmap row occupies ~44px (30px node + 14px gap). Grow the canvas
// with the word count so every word gets its own row — this is what keeps
// labels from overlapping when a root has dozens of linked words.
function containerHeight(): number {
  const words = props.graphData.nodes.filter((n) => n.data?.type === 'word').length
  return Math.max(520, words * 44 + 160)
}

function destroyGraph() {
  if (graph) { graph.destroy(); graph = null }
}

function buildGraph() {
  if (!containerRef.value) return
  containerRef.value.style.height = `${containerHeight()}px`
  graph = new Graph({
    container: containerRef.value,
    autoResize: true,
    // Mind-map layout: dagre with rankdir LR puts the morpheme (rank 0) on
    // the left and fans the words out in one column on the right, each word
    // on its own row. Edges are reversed (morpheme -> word) so the morpheme
    // lands in rank 0.
    data: {
      nodes: props.graphData.nodes.map((n) => ({ id: n.id, data: n.data, label: n.label })),
      edges: props.graphData.edges.map((e) => ({ source: e.target, target: e.source })),
    },
    node: {
      type: 'rect',
      style: (d: Record<string, unknown>) => {
        const data = d.data as Record<string, unknown> | undefined
        const isWord = data?.type === 'word'
        const [w, h] = nodeSize(String(d.label ?? ''), isWord)
        return {
          size: [w, h],
          fill: isWord ? '#ede9fe' : '#fde68a',
          radius: isWord ? 10 : 14,
          stroke: isWord ? '#818cf8' : '#f59e0b',
          lineWidth: isWord ? 1.5 : 2,
          shadowBlur: isWord ? 8 : 14,
          shadowColor: isWord ? 'rgba(99, 102, 241, 0.25)' : 'rgba(245, 158, 11, 0.3)',
          labelText: d.label,
          labelFill: isWord ? '#1e1b4b' : '#78350f',
          labelFontSize: isWord ? 13 : 15,
          labelFontWeight: isWord ? 500 : 700,
        }
      },
    },
    edge: {
      type: 'cubic-horizontal',
      style: { stroke: 'rgba(99, 102, 241, 0.4)', lineWidth: 1.5 },
    },
    layout: { type: 'dagre', rankdir: 'LR', nodesep: 14, ranksep: 110 },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
  })
  graph.on('node:click', (event: unknown) => {
    const ev = event as { target?: { id?: unknown } }
    const id = ev?.target?.id
    if (id == null) return
    const matched = props.graphData.nodes.find((n) => n.id === String(id))
    if (matched && matched.data?.type === 'word') {
      const wordId = matched.data.id
      if (typeof wordId === 'number') emit('select-word', wordId)
    }
  })
}

async function renderGraph() {
  if (!graph) { buildGraph() }
  if (!graph) return
  try { await graph.render() } catch (err) { console.warn('G6 render error:', err) }
}

onMounted(() => { renderGraph() })
// Rebuild on data change: the canvas height depends on the word count.
watch(() => props.graphData, () => { destroyGraph(); renderGraph() })
onBeforeUnmount(destroyGraph)
</script>

<template>
  <div ref="containerRef" class="graph-container"></div>
</template>

<style scoped>
.graph-container { width: 100%; min-height: 520px; border: 1px solid rgba(99, 102, 241, 0.08); border-radius: var(--lg-radius-lg); background: rgba(255, 255, 255, 0.4); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
</style>
