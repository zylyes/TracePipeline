<template>
  <div class="config-form">
    <el-form :model="form" label-width="100px" size="small">
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
      <el-form-item label="颜色">
        <div class="color-picker-group">
          <div class="color-picker-item">
            <span class="color-label">迹线</span>
            <el-color-picker v-model="style.trace_line_color" @change="emitStyle" />
          </div>
          <div class="color-picker-item">
            <span class="color-label">凸包</span>
            <el-color-picker v-model="style.hull_line_color" @change="emitStyle" />
          </div>
          <div class="color-picker-item">
            <span class="color-label">圆窗</span>
            <el-color-picker v-model="style.circle_window_line_color" @change="emitStyle" />
          </div>
          <div class="color-picker-item">
            <span class="color-label">玫瑰柱</span>
            <el-color-picker v-model="style.rose_bar_color" @change="emitStyle" />
          </div>
          <div class="color-picker-item">
            <span class="color-label">玫瑰边</span>
            <el-color-picker v-model="style.rose_bar_edge" @change="emitStyle" />
          </div>
          <div class="color-picker-item">
            <span class="color-label">网格</span>
            <el-color-picker v-model="style.rose_grid_color" @change="emitStyle" />
          </div>
        </div>
      </el-form-item>
      <el-form-item label="迹线线宽">
        <div class="slider-input-combo">
          <el-slider v-model="style.trace_line_width" :min="0.1" :max="3" :step="0.05" :format-tooltip="(v: number) => v.toFixed(2)" @change="emitStyle" />
          <el-input-number v-model="style.trace_line_width" :min="0.1" :max="3" :step="0.05" :precision="2" :controls="false" size="small" style="width: 80px; flex-shrink: 0;" @change="emitStyle" />
        </div>
      </el-form-item>
      <el-form-item label="凸包透明度">
        <div class="slider-input-combo">
          <el-slider v-model="style.hull_fill_alpha" :min="0" :max="1" :step="0.01" :format-tooltip="(v: number) => Math.round(v * 100) + '%'" @change="emitStyle" />
          <el-input-number :model-value="Math.round(style.hull_fill_alpha * 100)" :min="0" :max="100" :step="1" :controls="false" size="small" style="width: 80px; flex-shrink: 0;" @update:model-value="(val: number) => { style.hull_fill_alpha = val / 100; emitStyle() }" />
        </div>
      </el-form-item>
      <el-form-item label="圆窗透明度">
        <div class="slider-input-combo">
          <el-slider v-model="style.circle_window_fill_alpha" :min="0" :max="1" :step="0.01" :format-tooltip="(v: number) => Math.round(v * 100) + '%'" @change="emitStyle" />
          <el-input-number :model-value="Math.round(style.circle_window_fill_alpha * 100)" :min="0" :max="100" :step="1" :controls="false" size="small" style="width: 80px; flex-shrink: 0;" @update:model-value="(val: number) => { style.circle_window_fill_alpha = val / 100; emitStyle() }" />
        </div>
      </el-form-item>
      <el-form-item label="标题字号">
        <div class="slider-input-combo">
          <el-slider v-model="style.title_font_size" :min="8" :max="16" :step="0.5" @change="emitStyle" />
          <el-input-number v-model="style.title_font_size" :min="8" :max="16" :step="0.5" :controls="false" size="small" style="width: 80px; flex-shrink: 0;" @change="emitStyle" />
        </div>
      </el-form-item>
      <el-form-item label="节点样式">
        <div class="style-action-row">
          <el-select v-model="style.node_style" style="width: 130px" @change="emitStyle">
            <template #prefix>
              <svg v-if="style.node_style === 'default'" class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#e8e8e8" stroke="#909399" stroke-width="1"/></svg>
              <svg v-else-if="style.node_style === 'solid'" class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#409eff" stroke="#409eff" stroke-width="1"/></svg>
              <svg v-else-if="style.node_style === 'hollow'" class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#fff" stroke="#2c3e50" stroke-width="1.5"/></svg>
              <svg v-else-if="style.node_style === 'dark'" class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#2c3e50" stroke="#2c3e50" stroke-width="1"/></svg>
            </template>
            <el-option label="默认" value="default">
              <span class="node-option">
                <svg class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#e8e8e8" stroke="#909399" stroke-width="1"/></svg>
                <span>默认</span>
              </span>
            </el-option>
            <el-option label="实心" value="solid">
              <span class="node-option">
                <svg class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#409eff" stroke="#409eff" stroke-width="1"/></svg>
                <span>实心</span>
              </span>
            </el-option>
            <el-option label="空心" value="hollow">
              <span class="node-option">
                <svg class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#fff" stroke="#2c3e50" stroke-width="1.5"/></svg>
                <span>空心</span>
              </span>
            </el-option>
            <el-option label="深色" value="dark">
              <span class="node-option">
                <svg class="node-icon" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="#2c3e50" stroke="#2c3e50" stroke-width="1"/></svg>
                <span>深色</span>
              </span>
            </el-option>
          </el-select>
          <el-button type="primary" size="small" :icon="BrushIcon" @click="$emit('save-style')">保存样式设置</el-button>
          <el-button size="small" :icon="RefreshLeftIcon" @click="$emit('reset-style')">重置样式设置</el-button>
        </div>
      </el-form-item>

    </el-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Brush as BrushIcon, RefreshLeft as RefreshLeftIcon } from '@element-plus/icons-vue'
import { api } from '@/api/pywebview'
import type { ConfigData } from '@/types'

const props = defineProps<{
  modelValue: ConfigData
  styleConfig: ConfigData
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: ConfigData): void
  (e: 'styleChange', val: ConfigData): void
  (e: 'save-style'): void
  (e: 'reset-style'): void
}>()

const defaultForm: ConfigData = {
  input_dir: 'input',
  output_dir: 'output',
  process_all: true,
  node_label_mode: 'type',
}

const form = reactive<ConfigData>({ ...defaultForm, ...props.modelValue })
const style = ref<ConfigData>({ ...props.styleConfig })

watch(() => props.modelValue, (val) => {
  Object.assign(form, { ...defaultForm, ...val })
}, { deep: true })

watch(() => props.styleConfig, (val) => {
  style.value = { ...val }
}, { deep: true })

watch(form, (val) => {
  emit('update:modelValue', { ...val })
}, { deep: true })

// 路径自动保存（带竞态保护）
let pathSaving = false
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
      if (pathSaving) return
      pathSaving = true
      try {
        await api.set_config(payload)
      } catch (e) {
        console.warn('路径自动保存失败', e)
      } finally {
        pathSaving = false
      }
    }
  },
  { immediate: false }
)

function emitStyle() {
  emit('styleChange', { ...style.value })
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
.config-form {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  :deep(.el-form-item) {
    margin-bottom: 16px;
  }
  :deep(.el-form-item__label) {
    font-weight: 500;
    color: #606266;
  }
}
.config-form h3 {
  position: relative;
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 20px 0 12px;
  padding-bottom: 8px;
  padding-left: 10px;
  border-bottom: 1px solid #e4e7ed;
}
.config-form h3:first-of-type {
  margin-top: 0;
}
.config-form h3::before {
  content: '';
  position: absolute;
  left: 0;
  top: 2px;
  bottom: 8px;
  width: 3px;
  background: #409eff;
  border-radius: 2px;
}
.slider-input-combo {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}
.slider-input-combo .el-slider {
  flex: 1;
}
.color-picker-group {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
}
.color-picker-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px 4px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
  transition: background 0.2s;
}
.color-picker-item:hover {
  background: #eef1f6;
}
.color-label {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}
@media (max-width: 768px) {
  .color-picker-group {
    grid-template-columns: repeat(3, 1fr);
  }
  .style-action-row {
    flex-wrap: wrap;
  }
}
.style-action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
  width: 100%;
}
.style-action-row .el-select {
  flex-shrink: 0;
}
.style-action-row .el-button:first-of-type {
  margin-left: auto;
}
.node-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.node-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
:deep(.el-select__prefix) {
  display: inline-flex;
  align-items: center;
}
</style>
