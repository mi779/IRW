<script setup lang="ts">
import { computed } from 'vue'
import type { Morpheme, Word } from '@/types'

const props = defineProps<{ word: Word }>()

type MorphemeType = 'prefix' | 'stem' | 'root' | 'suffix'

interface BreakdownItem {
  key: string
  type: MorphemeType
  display: string
  meaning: string | null
}

const TYPE_LABELS: Record<MorphemeType, string> = {
  prefix: '前缀',
  stem: '词干',
  root: '词根',
  suffix: '后缀',
}

function cleanText(t: string): string {
  return t.replace(/^-+|-+$/g, '')
}

// A word may link to overlapping morphemes (e.g. suffixes "tion" and "ion");
// keep only the longest of each overlapping group.
function dedupeMorphemes(list: Morpheme[], mode: 'prefix' | 'suffix'): Morpheme[] {
  const byText = new Map<string, Morpheme>()
  for (const m of list) {
    const t = cleanText(m.text).toLowerCase()
    if (!t) continue
    const prev = byText.get(t)
    if (!prev || (!prev.meaning && m.meaning)) byText.set(t, m)
  }
  const entries = [...byText.entries()]
  return entries
    .filter(([t, m]) => !entries.some(([ot, o]) => o !== m && ot.length > t.length && (mode === 'prefix' ? ot.startsWith(t) : ot.endsWith(t))))
    .map(([, m]) => m)
}

const breakdown = computed(() => {
  const prefixes = dedupeMorphemes(props.word.prefixes ?? [], 'prefix')
  const roots = props.word.roots ?? []
  const suffixes = dedupeMorphemes(props.word.suffixes ?? [], 'suffix')
  const spelling = props.word.spelling.toLowerCase()

  // Place morphemes as non-overlapping intervals on the spelling:
  // prefixes anchor at the start, roots anywhere, suffixes at the end
  // (longest first). Only placed morphemes are displayed, which filters
  // overlapping false positives (e.g. a "tin" root inside "unsuspecting").
  const spans: [number, number][] = []
  const overlaps = (a: number, b: number) => spans.some(([s, e]) => a < e && b > s)

  const placedPrefixes: Morpheme[] = []
  for (const p of prefixes) {
    const t = cleanText(p.text).toLowerCase()
    if (t && spelling.startsWith(t) && !overlaps(0, t.length)) {
      spans.push([0, t.length])
      placedPrefixes.push(p)
    }
  }
  const placedRoots: Morpheme[] = []
  for (const r of roots) {
    const t = cleanText(r.text).toLowerCase()
    if (!t) continue
    let idx = spelling.indexOf(t)
    while (idx >= 0 && overlaps(idx, idx + t.length)) idx = spelling.indexOf(t, idx + 1)
    if (idx >= 0) {
      spans.push([idx, idx + t.length])
      placedRoots.push(r)
    }
  }
  const placedSuffixes: Morpheme[] = []
  for (const s of [...suffixes].sort((a, b) => cleanText(b.text).length - cleanText(a.text).length)) {
    const t = cleanText(s.text).toLowerCase()
    const idx = t ? spelling.length - t.length : -1
    if (idx >= 0 && spelling.endsWith(t) && !overlaps(idx, spelling.length)) {
      spans.push([idx, spelling.length])
      placedSuffixes.push(s)
    }
  }

  // Stem = letters not covered by any placed morpheme.
  let stem = ''
  let cursor = 0
  for (const [s, e] of [...spans].sort((a, b) => a[0] - b[0])) {
    if (s > cursor) stem += spelling.slice(cursor, s)
    cursor = Math.max(cursor, e)
  }
  if (cursor < spelling.length) stem += spelling.slice(cursor)

  const items: BreakdownItem[] = [
    ...placedPrefixes.map((m) => ({ key: `p-${m.id}`, type: 'prefix' as const, display: `${cleanText(m.text)}-`, meaning: m.meaning })),
    ...placedRoots.map((m) => ({ key: `r-${m.id}`, type: 'root' as const, display: cleanText(m.text), meaning: m.meaning })),
  ]
  if (stem.length >= 2 && items.length > 0) {
    items.push({ key: 'stem', type: 'stem', display: stem, meaning: null })
  }
  items.push(
    ...placedSuffixes.map((m) => ({ key: `s-${m.id}`, type: 'suffix' as const, display: `-${cleanText(m.text)}`, meaning: m.meaning })),
  )

  const formula = items
    .map((i) => (i.meaning ? `${cleanText(i.display)}(${i.meaning})` : cleanText(i.display)))
    .join(' ＋ ')
  let firstDef = props.word.definitions?.[0]?.text ?? ''
  if (firstDef.length > 40) firstDef = firstDef.slice(0, 40) + '…'

  // Breakdown is only meaningful with at least one placed root or prefix.
  return { items, formula, firstDef, has: placedPrefixes.length + placedRoots.length > 0 }
})
</script>

<template>
  <div class="word-card lg-glass">
    <div class="card-head">
      <div class="spelling">{{ word.spelling }}</div>
      <div v-if="word.phonetics" class="phonetics">
        <span v-for="(value, key) in word.phonetics" :key="key" class="phonetic-chip">
          <span class="pho-key">{{ key }}</span>
          <span class="pho-val">{{ value }}</span>
        </span>
      </div>
    </div>
    <div v-if="word.definitions?.length" class="section">
      <div class="section-title"><span class="title-bar"></span>释义</div>
      <ul class="definitions">
        <li v-for="(def, idx) in word.definitions" :key="idx">
          <span class="pos">{{ def.pos }}</span>
          <span class="text">{{ def.text }}</span>
        </li>
      </ul>
    </div>
    <div v-if="word.example_sentences?.length" class="section">
      <div class="section-title"><span class="title-bar"></span>例句</div>
      <ul class="examples"><li v-for="(sentence, idx) in word.example_sentences" :key="idx">{{ sentence }}</li></ul>
    </div>
    <div v-if="breakdown.has" class="section">
      <div class="section-title"><span class="title-bar"></span>构词拆解</div>
      <div class="bd-formula">
        <span class="bd-word">{{ word.spelling }}</span>
        <span class="bd-eq">＝</span>
        <span class="bd-parts">{{ breakdown.formula }}</span>
        <template v-if="breakdown.firstDef">
          <span class="bd-arrow">→</span>
          <span class="bd-def">{{ breakdown.firstDef }}</span>
        </template>
      </div>
      <ul class="bd-lines">
        <li v-for="item in breakdown.items" :key="item.key" :class="'bd-' + item.type">
          <span class="bd-type">{{ TYPE_LABELS[item.type] }}</span>
          <span class="bd-text">{{ item.display }}</span>
          <span class="bd-meaning">{{ item.meaning ?? '—' }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.word-card { width: 100%; padding: 28px; border-radius: var(--lg-radius-xl); }
.card-head { margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid rgba(99, 102, 241, 0.1); }
.spelling { font-size: 32px; font-weight: 700; color: var(--lg-text-primary); margin-bottom: 10px; letter-spacing: -0.01em; }
.phonetics { display: flex; flex-wrap: wrap; gap: 8px; }
.phonetic-chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: rgba(99, 102, 241, 0.08); border-radius: var(--lg-radius-pill); font-size: 13px; }
.pho-key { font-weight: 600; color: var(--lg-info); text-transform: uppercase; font-size: 11px; }
.pho-val { color: var(--lg-text-secondary); font-family: 'SF Mono', Consolas, monospace; font-size: 13px; }
.section { margin-top: 20px; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: var(--lg-text-primary); margin-bottom: 10px; }
.title-bar { width: 3px; height: 14px; border-radius: 2px; background: var(--lg-gradient-primary); }
.definitions, .examples { margin: 0; padding-left: 16px; }
.definitions li, .examples li { margin-bottom: 8px; color: var(--lg-text-secondary); line-height: 1.6; }
.pos { display: inline-block; min-width: 44px; padding: 1px 8px; background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(236, 72, 153, 0.1)); border-radius: var(--lg-radius-xs); color: #d97706; font-style: italic; font-size: 12px; font-weight: 600; text-align: center; margin-right: 8px; }
.bd-formula { padding: 10px 14px; background: rgba(99, 102, 241, 0.06); border-radius: var(--lg-radius-md); font-size: 14px; line-height: 1.8; color: var(--lg-text-secondary); }
.bd-word { font-weight: 700; color: var(--lg-text-primary); }
.bd-eq, .bd-arrow { margin: 0 6px; color: var(--lg-text-tertiary); }
.bd-def { color: var(--lg-text-primary); }
.bd-lines { margin: 12px 0 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
.bd-lines li { display: flex; align-items: center; gap: 10px; padding: 6px 12px; border-radius: var(--lg-radius-md); background: rgba(255, 255, 255, 0.45); }
.bd-type { flex-shrink: 0; width: 42px; text-align: center; font-size: 11px; font-weight: 600; padding: 2px 0; border-radius: var(--lg-radius-xs); }
.bd-prefix .bd-type { background: rgba(99, 102, 241, 0.12); color: #4f46e5; }
.bd-root .bd-type { background: rgba(16, 185, 129, 0.12); color: #059669; }
.bd-stem .bd-type { background: rgba(100, 116, 139, 0.12); color: #64748b; }
.bd-suffix .bd-type { background: rgba(245, 158, 11, 0.14); color: #be185d; }
.bd-text { font-family: 'SF Mono', Consolas, monospace; font-weight: 600; color: var(--lg-text-primary); min-width: 70px; }
.bd-meaning { color: var(--lg-text-secondary); font-size: 13px; }
</style>
