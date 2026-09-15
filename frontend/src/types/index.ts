export interface Definition {
  pos: string
  text: string
}

export interface Morpheme {
  id: number
  text: string
  meaning: string | null
  description: string | null
}

export interface Word {
  id: number
  spelling: string
  phonetics: Record<string, string> | null
  definitions: Definition[] | null
  part_of_speech: string | null
  example_sentences: string[] | null
  created_at: string
  roots?: Morpheme[]
  prefixes?: Morpheme[]
  suffixes?: Morpheme[]
}

export interface ReviewQueueItem {
  word_id: number
  spelling: string
  due_date: string
  ease_factor: number
  repetitions: number
}

export interface G6Node {
  id: string
  label: string
  data: Record<string, unknown>
}

export interface G6Edge {
  source: string
  target: string
  label?: string
}

export interface GraphData {
  nodes: G6Node[]
  edges: G6Edge[]
}
