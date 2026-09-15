<script setup lang="ts">
import { reactive, ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useWordStore } from '@/stores/word'
import { useMorphemeStore } from '@/stores/morpheme'
import type { Word } from '@/types'

const props = defineProps<{
  modelValue: boolean
  word?: Word | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const wordStore = useWordStore()
const morphemeStore = useMorphemeStore()

const submitting = ref(false)

interface FormState {
  spelling: string
  phonetics_us: string
  phonetics_uk: string
  definitions: { pos: string; text: string }[]
  example_sentences: string[]
  root_ids: number[]
  prefix_ids: number[]
  suffix_ids: number[]
}

const defaultForm = (): FormState => ({
  spelling: '',
  phonetics_us: '',
  phonetics_uk: '',
  definitions: [{ pos: '', text: '' }],
  example_sentences: [''],
  root_ids: [],
  prefix_ids: [],
  suffix_ids: [],
})

const form = reactive<FormState>(defaultForm())

const isEdit = computed(() => !!props.word?.id)

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    if (props.word) {
      form.spelling = props.word.spelling
      form.phonetics_us = props.word.phonetics?.us ?? ''
      form.phonetics_uk = props.word.phonetics?.uk ?? ''
      form.definitions =
        props.word.definitions && props.word.definitions.length
          ? props.word.definitions.map((d) => ({ pos: d.pos, text: d.text }))
          : [{ pos: '', text: '' }]
      form.example_sentences = props.word.example_sentences?.length
        ? [...props.word.example_sentences]
        : ['']
      form.root_ids = props.word.roots?.map((r) => r.id) ?? []
      form.prefix_ids = props.word.prefixes?.map((p) => p.id) ?? []
      form.suffix_ids = props.word.suffixes?.map((s) => s.id) ?? []
    } else {
      Object.assign(form, defaultForm())
    }
    morphemeStore.fetchRoots().catch(() => {})
    morphemeStore.fetchPrefixes().catch(() => {})
    morphemeStore.fetchSuffixes().catch(() => {})
  },
)

function addDefinition() {
  form.definitions.push({ pos: '', text: '' })
}

function removeDefinition(idx: number) {
  form.definitions.splice(idx, 1)
}

function addExample() {
  form.example_sentences.push('')
}

function removeExample(idx: number) {
  form.example_sentences.splice(idx, 1)
}

function buildPayload() {
  const phonetics: Record<string, string> = {}
  if (form.phonetics_us) phonetics.us = form.phonetics_us
  if (form.phonetics_uk) phonetics.uk = form.phonetics_uk
  return {
    spelling: form.spelling,
    phonetics: Object.keys(phonetics).length ? phonetics : null,
    definitions: form.definitions.filter((d) => d.text).length
      ? form.definitions.filter((d) => d.text)
      : null,
    example_sentences: form.example_sentences.filter((s) => s).length
      ? form.example_sentences.filter((s) => s)
      : null,
    root_ids: form.root_ids,
    prefix_ids: form.prefix_ids,
    suffix_ids: form.suffix_ids,
  }
}

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  if (!form.spelling.trim()) {
    ElMessage.warning('请输入单词拼写')
    return
  }
  submitting.value = true
  try {
    const payload = buildPayload()
    if (props.word?.id) {
      await wordStore.update(props.word.id, payload)
    } else {
      await wordStore.create(payload)
    }
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    emit('saved')
    close()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑单词' : '添加单词'"
    width="640px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-width="80px" label-position="right">
      <el-form-item label="拼写">
        <el-input v-model="form.spelling" placeholder="请输入单词拼写" />
      </el-form-item>
      <el-form-item label="音标 US">
        <el-input v-model="form.phonetics_us" placeholder="/us/" />
      </el-form-item>
      <el-form-item label="音标 UK">
        <el-input v-model="form.phonetics_uk" placeholder="/uk/" />
      </el-form-item>
      <el-form-item label="释义">
        <div class="dynamic-list">
          <div
            v-for="(def, idx) in form.definitions"
            :key="`def-${idx}`"
            class="dynamic-row"
          >
            <el-input v-model="def.pos" placeholder="词性" class="pos-input" />
            <el-input v-model="def.text" placeholder="释义" class="text-input" />
            <el-button type="danger" link @click="removeDefinition(idx)">删除</el-button>
          </div>
          <el-button link type="primary" @click="addDefinition">+ 添加释义</el-button>
        </div>
      </el-form-item>
      <el-form-item label="例句">
        <div class="dynamic-list">
          <div
            v-for="(_, idx) in form.example_sentences"
            :key="`ex-${idx}`"
            class="dynamic-row"
          >
            <el-input v-model="form.example_sentences[idx]" placeholder="例句" class="text-input" />
            <el-button type="danger" link @click="removeExample(idx)">删除</el-button>
          </div>
          <el-button link type="primary" @click="addExample">+ 添加例句</el-button>
        </div>
      </el-form-item>
      <el-form-item label="词根">
        <el-select v-model="form.root_ids" multiple filterable placeholder="选择词根" style="width: 100%">
          <el-option
            v-for="r in morphemeStore.roots"
            :key="r.id"
            :label="`${r.text}${r.meaning ? ' - ' + r.meaning : ''}`"
            :value="r.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="前缀">
        <el-select v-model="form.prefix_ids" multiple filterable placeholder="选择前缀" style="width: 100%">
          <el-option
            v-for="p in morphemeStore.prefixes"
            :key="p.id"
            :label="`${p.text}${p.meaning ? ' - ' + p.meaning : ''}`"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="后缀">
        <el-select v-model="form.suffix_ids" multiple filterable placeholder="选择后缀" style="width: 100%">
          <el-option
            v-for="s in morphemeStore.suffixes"
            :key="s.id"
            :label="`${s.text}${s.meaning ? ' - ' + s.meaning : ''}`"
            :value="s.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dynamic-list {
  width: 100%;
}

.dynamic-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}

.pos-input {
  width: 120px;
  flex-shrink: 0;
}

.text-input {
  flex: 1;
}
</style>
