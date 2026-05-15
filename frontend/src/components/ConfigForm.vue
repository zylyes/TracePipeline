<template>
  <div class="config-form">
    <el-form :model="form" label-width="140px" size="small">
      <h3>路径</h3>
      <el-form-item label="输入目录">
        <el-input v-model="form.input_dir">
          <template #append><el-button @click="browse('input')">浏览</el-button></template>
        </el-input>
      </el-form-item>
      <el-form-item label="输出目录">
        <el-input v-model="form.output_dir">
          <template #append><el-button @click="browse('output')">浏览</el-button></template>
        </el-input>
      </el-form-item>

      <h3>绘图样式</h3>
      <el-form-item label="迹线颜色">
        <el-color-picker v-model="style.trace_line_color" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="线宽">
        <el-slider v-model="style.trace_line_width" :min="0.1" :max="3" :step="0.05" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="凸包颜色">
        <el-color-picker v-model="style.hull_line_color" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="凸包透明度">
        <el-slider v-model="style.hull_fill_alpha" :min="0" :max="1" :step="0.01" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="圆窗颜色">
        <el-color-picker v-model="style.circle_window_line_color" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="圆窗透明度">
        <el-slider v-model="style.circle_window_fill_alpha" :min="0" :max="1" :step="0.01" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="玫瑰柱体">
        <el-color-picker v-model="style.rose_bar_color" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="玫瑰边框">
        <el-color-picker v-model="style.rose_bar_edge" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="网格颜色">
        <el-color-picker v-model="style.rose_grid_color" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="全局字号">
        <el-slider v-model="style.global_font_size" :min="6" :max="14" :step="0.5" @change="emitStyle" />
      </el-form-item>
      <el-form-item label="节点标签模式">
        <el-select v-model="form.node_label_mode" style="width: 200px">
          <el-option label="类型" value="type" />
          <el-option label="ID" value="id" />
          <el-option label="无" value="none" />
        </el-select>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { api } from '@/api/pywebview'
import type { ConfigData } from '@/types'

const props = defineProps<{
  modelValue: ConfigData
  styleConfig: ConfigData
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: ConfigData): void
  (e: 'styleChange', val: ConfigData): void
}>()

const defaultForm: ConfigData = {
  input_dir: 'input',
  output_dir: 'output',
  process_all: true,
  node_label_mode: 'type',
}

const form = reactive<ConfigData>({ ...defaultForm, ...props.modelValue })
const style = reactive<ConfigData>({ ...props.styleConfig })

watch(() => props.modelValue, (val) => {
  Object.assign(form, { ...defaultForm, ...val })
}, { deep: true })

watch(() => props.styleConfig, (val) => {
  Object.assign(style, val)
}, { deep: true })

watch(form, (val) => {
  emit('update:modelValue', { ...val })
}, { deep: true })

// 路径自动保存
watch(
  () => [form.input_dir, form.output_dir],
  async ([newInput, newOutput], [oldInput, oldOutput]) => {
    const payload: Record<string, any> = {}
    if (newInput !== oldInput && newInput) {
      payload.input_dir = newInput
    }
    if (newOutput !== oldOutput && newOutput) {
      payload.output_dir = newOutput
    }
    if (Object.keys(payload).length > 0) {
      try {
        await api.set_config(payload)
      } catch (e) {
        // 静默失败，避免干扰用户
        console.warn('路径自动保存失败', e)
      }
    }
  },
  { immediate: false }
)

function emitStyle() {
  emit('styleChange', { ...style })
}

async function browse(type: string) {
  const folder = await api.browse_folder()
  if (folder) {
    if (type === 'input') {
      form.input_dir = folder
    } else if (type === 'output') {
      form.output_dir = folder
    }
    emit('update:modelValue', { ...form })
  }
}
</script>

<style scoped lang="scss">
.config-form h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 16px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
</style>
