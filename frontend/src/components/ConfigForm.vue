<template>
  <div class="config-form tp-card tp-neon-edge">
    <el-form :model="form" label-width="100px" size="small">
      <div class="form-section">
        <h3 class="section-title">
          <div class="section-icon">
            <el-icon :size="14"><Folder /></el-icon>
          </div>
          <span>路径</span>
        </h3>
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
      </div>

      <div class="form-section">
        <h3 class="section-title">
          <div class="section-icon">
            <el-icon :size="14"><Brush /></el-icon>
          </div>
          <span>绘图样式</span>
        </h3>
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
            <el-input-number :model-value="Math.round((style.hull_fill_alpha ?? 0) * 100)" :min="0" :max="100" :step="1" :controls="false" size="small" style="width: 60px; flex-shrink: 0;" @update:model-value="(val: number) => { style.hull_fill_alpha = val / 100; emitStyle() }" />
            <span style="margin-left: 4px; color: var(--tp-text-secondary); font-size: 13px;">%</span>
          </div>
        </el-form-item>
        <el-form-item label="圆窗透明度">
          <div class="slider-input-combo">
            <el-slider v-model="style.circle_window_fill_alpha" :min="0" :max="1" :step="0.01" :format-tooltip="(v: number) => Math.round(v * 100) + '%'" @change="emitStyle" />
            <el-input-number :model-value="Math.round((style.circle_window_fill_alpha ?? 0) * 100)" :min="0" :max="100" :step="1" :controls="false" size="small" style="width: 60px; flex-shrink: 0;" @update:model-value="(val: number) => { style.circle_window_fill_alpha = val / 100; emitStyle() }" />
            <span style="margin-left: 4px; color: var(--tp-text-secondary); font-size: 13px;">%</span>
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
      </div>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onUnmounted, reactive, ref, watch } from 'vue'
import { Brush as BrushIcon, RefreshLeft as RefreshLeftIcon, Folder, Brush } from '@element-plus/icons-vue'
import { api } from '@/api/pywebview'
import { useConfigStore } from '@/stores/config'
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
const configStore = useConfigStore()
let syncingFromProps = false

watch(() => props.modelValue, (val) => {
  syncingFromProps = true
  Object.assign(form, { ...defaultForm, ...val })
  void nextTick(() => {
    syncingFromProps = false
  })
}, { deep: true })

watch(() => props.styleConfig, (val) => {
  style.value = { ...val }
}, { deep: true })

watch(form, (val) => {
  emit('update:modelValue', { ...val })
}, { deep: true })

// 路径自动保存（简化版：debounce + last-write-wins）
const PATH_SAVE_DEBOUNCE_MS = 400
let pathSaveTimer: number | null = null
let pathSaveInFlight = false
let pendingPathPayload: Record<string, any> = {}

function hasPendingPathPayload() {
  return Object.keys(pendingPathPayload).length > 0
}

function schedulePathSave(payload: Record<string, any>) {
  pendingPathPayload = { ...pendingPathPayload, ...payload }
  if (pathSaveTimer !== null) {
    window.clearTimeout(pathSaveTimer)
  }
  pathSaveTimer = window.setTimeout(() => {
    pathSaveTimer = null
    void flushPathSave()
  }, PATH_SAVE_DEBOUNCE_MS)
}

async function flushPathSave() {
  if (!hasPendingPathPayload()) return
  if (pathSaveInFlight) return

  pathSaveInFlight = true
  let saveFailed = false
  const payload = { ...pendingPathPayload }
  pendingPathPayload = {}
  try {
    const saved = await configStore.saveConfig(payload)
    emit('update:modelValue', { ...saved })
  } catch (e) {
    // 保存失败：合并回待保存对象，等待下次修改重试
    pendingPathPayload = { ...payload, ...pendingPathPayload }
    saveFailed = true
    console.warn('路径自动保存失败', e)
  } finally {
    pathSaveInFlight = false
    if (!saveFailed && hasPendingPathPayload()) {
      schedulePathSave({})
    }
  }
}
watch(
  () => [form.input_dir, form.output_dir],
  ([newInput, newOutput], [oldInput, oldOutput]) => {
    if (syncingFromProps) return
    const payload: Record<string, any> = {}
    if (newInput !== oldInput && newInput) {
      payload.input_dir = newInput
    }
    if (newOutput !== oldOutput && newOutput) {
      payload.output_dir = newOutput
    }
    if (Object.keys(payload).length > 0) {
      schedulePathSave(payload)
    }
  },
  { immediate: false }
)

onUnmounted(() => {
  if (pathSaveTimer !== null) {
    window.clearTimeout(pathSaveTimer)
    pathSaveTimer = null
  }
  if (hasPendingPathPayload()) {
    void flushPathSave()
  }
})

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
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-bottom: var(--tp-space-4);
}

.form-section {
  margin-bottom: var(--tp-space-4);
}

.form-section:last-child {
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0 0 var(--tp-space-3);
  padding-bottom: var(--tp-space-2);
  border-bottom: 1px solid var(--tp-border-light);
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 96px;
  height: 1px;
  background: linear-gradient(90deg, var(--tp-brand-accent-light), transparent);
}

.section-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-info-bg);
  color: var(--tp-info);
}

.section-title:first-of-type {
  margin-top: 0;
}

:deep(.el-form-item) {
  margin-bottom: var(--tp-space-3);
}

:deep(.el-form-item__label) {
  font-family: var(--tp-font-heading);
  font-weight: 500;
  color: var(--tp-text-secondary);
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
  padding: 10px 4px;
  background: rgba(238, 240, 244, 0.76);
  border-radius: var(--tp-radius-md);
  border: 1px solid var(--tp-border-light);
  transition: all var(--tp-duration-normal);
}

.color-picker-item:hover {
  background: rgba(232, 236, 241, 0.92);
  box-shadow: var(--tp-shadow-sm), var(--tp-glow-cyan-sm);
  transform: translateY(-1px);
}

.color-label {
  font-family: var(--tp-font-heading);
  font-size: 12px;
  color: var(--tp-text-tertiary);
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
  font-family: var(--tp-font-body);
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
