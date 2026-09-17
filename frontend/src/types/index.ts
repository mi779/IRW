export interface Definition {
  pos: string
  text: string
}

export interface Morpheme {
  id: number
  text: string
  meaning: string | null
  description: string | null
  word_count?: number | null
}

export interface Word {
  id: number
  spelling: string
  phonetics: Record<string, string> | null
  definitions: Definition[] | null
  part_of_speech: string | null
  tags: string[] | null
  bnc?: number | null
  frq?: number | null
  example_sentences: string[] | null
  created_at: string
  roots?: Morpheme[]
  prefixes?: Morpheme[]
  suffixes?: Morpheme[]
}

export interface WordRelation {
  related_word: string
  relation: string
  pos: string | null
  gloss_cn: string | null
}

export interface WordPhrase {
  phrase: string
  pos: string | null
  gloss_cn: string | null
  gloss_en: string | null
}

export interface WordRelated {
  synonyms: WordRelation[]
  antonyms: WordRelation[]
  phrases: WordPhrase[]
}

export interface WordPage {
  total: number
  items: Word[]
  skip: number
  limit: number
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
