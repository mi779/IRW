<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Graph } from '@antv/g6'
import type { GraphData } from '@/types'

const props = defineProps<{ graphData: GraphData }>()

const emit = defineEmits<{
  (e: 'select-word', wordId: number): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let graph: Graph | null = null

const HEIGHT = 500

function buildGraph() {
  if (!containerRef.value) return
  const width = containerRef.value.clientWidth || 800
  graph = new Graph({
    container: containerRef.value,
    autoResize: true,
    data: {
      nodes: props.graphData.nodes.map((n) => ({ id: n.id, data: n.data, label: n.label })),
      edges: props.graphData.edges.map((e) => ({ source: e.source, target: e.target })),
    },
    node: {
      type: 'rect',
      style: (d: Record<string, unknown>) => {
        const data = d.data as Record<string, unknown> | undefined
        const label = d.label as string | number | undefined
        const nodeType = data?.type
        return {
          fill:
            nodeType === 'root' || nodeType === 'prefix' || nodeType === 'suffix'
              ? '#ffd591'
              : '#e6f4ff',
          radius: 8,
          stroke: '#d9d9d9',
          labelText: label,
          labelFill: '#333',
        }
      },
    },
    edge: {
      type: 'line',
      style: { endArrow: true },
    },
    layout: {
      type: 'radial',
      width,
      height: HEIGHT,
      linkDistance: 120,
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
  })

  graph.on('node:click', (event: unknown) => {
    const ev = event as { target?: { id?: unknown } }
    const id = ev?.target?.id
    if (id == null) return
    const matched = props.graphData.nodes.find((n) => n.id === String(id))
    if (matched && matched.data?.type === 'word') {
      const wordId = matched.data.id
      if (typeof wordId === 'number') {
        emit('select-word', wordId)
      }
    }
  })
}

async function renderGraph() {
  if (!graph) {
    buildGraph()
  }
  if (!graph) return
  graph.setData({
    nodes: props.graphData.nodes.map((n) => ({ id: n.id, data: n.data, label: n.label })),
    edges: props.graphData.edges.map((e) => ({ source: e.source, target: e.target })),
  })
  try {
    await graph.render()
  } catch (err) {
    // Render can throw if container is not ready; ignore
    console.warn('G6 render error:', err)
  }
}

onMounted(async () => {
  buildGraph()
  await renderGraph()
})

watch(
  () => props.graphData,
  () => {
    renderGraph()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (graph) {
    graph.destroy()
    graph = null
  }
})
</script>

<template>
  <div ref="containerRef" class="graph-container"></div>
</template>

<style scoped>
.graph-container {
  width: 100%;
  height: 500px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background-color: #fafafa;
}
</style>
