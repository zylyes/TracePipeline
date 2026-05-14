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

      <h3>输出控制</h3>
      <el-form-item label="导出玫瑰图">
        <el-switch v-model="form.export_rose_plot" />
      </el-form-item>
      <el-form-item label="玫瑰图 DPI">
        <el-select v-model="form.rose_dpi">
          <el-option v-for="d in [200,300,400,600]" :key="d" :label="d" :value="d" />
        </el-select>
      </el-form-item>
      <el-form-item label="分箱宽度">
        <el-select v-model="form.rose_bin_width">
          <el-option v-for="b in [5,10,15,20,30]" :key="b" :label="b + '°'" :value="b" />
        </el-select>
      </el-form-item>
      <el-form-item label="原始迹线图 DPI">
        <el-select v-model="form.trace_dpi">
          <el-option v-for="d in [150,200,300,400,600]" :key="d" :label="d" :value="d" />
        </el-select>
      </el-form-item>
      <el-form-item label="旋转迹线图 DPI">
        <el-select v-model="form.rotated_trace_dpi">
          <el-option v-for="d in [300,400,600,800]" :key="d" :label="d" :value="d" />
        </el-select>
      </el-form-item>

      <h3>圆窗策略</h3>
      <el-form-item label="策略选择">
        <el-select v-model="form.window_strategy">
          <el-option label="auto" value="auto" />
          <el-option label="tangent" value="tangent" />
          <el-option label="hybrid" value="hybrid" />
          <el-option label="concentric" value="concentric" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.window_strategy === 'auto'" label="密度阈值">
        <el-input-number v-model="form.auto_density_threshold" :min="1" :max="20" :step="0.5" />
      </el-form-item>
      <el-form-item v-if="form.window_strategy === 'tangent'" label="切圆数量">
        <el-input-number v-model="form.tangent_window_count" :min="1" :max="10" />
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
  export_rose_plot: true,
  rose_bin_width: 10,
  rose_dpi: 400,
  trace_dpi: 300,
  rotated_trace_dpi: 600,
  window_strategy: 'auto',
  auto_density_threshold: 5.0,
  tangent_window_count: 3,
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
