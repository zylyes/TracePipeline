<template>
  <div class="config-view">
    <h2 class="page-title">配置</h2>
    <ConfigForm v-model="form" :style-config="styleConfig" @style-change="onStyleChange" @save-style="saveStyleConfig" @reset-style="resetStyleConfig" />
    <StylePreview :style-config="styleConfig" :preview-trigger="previewTrigger" @save-style="saveStyleConfig" @reset-style="resetStyleConfig" />
    <DevPanel v-show="appStore.isDevMode" @saved="loadConfig" @reset="loadConfig" />

    <div class="action-bar tp-card tp-neon-edge">
      <div class="action-group primary">
        <el-button :icon="Refresh" @click="reloadConfig" size="small">重新加载配置</el-button>
        <el-button :icon="Upload" @click="triggerImportJSON" size="small">导入 JSON</el-button>
        <el-button :icon="Download" @click="exportJSON" size="small">导出 JSON</el-button>
      </div>
      <div class="action-divider"></div>
      <div class="action-group secondary">
        <el-button :icon="Setting" @click="resetProcessingConfig" size="small" type="warning" plain>重置处理设置</el-button>
        <el-button :icon="RefreshRight" @click="resetAllConfig" size="small" type="danger" plain>重置所有设置</el-button>
      </div>
      <input ref="fileInputRef" type="file" accept=".json" style="display: none" @change="importJSON" />
    </div>

  </div>
</template>

<script setup lang="ts">
import { h, ref, onMounted, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { msg } from '@/utils/message'
import { Refresh, Download, RefreshRight, Setting, Upload } from '@element-plus/icons-vue'
import ConfigForm from '@/components/ConfigForm.vue'
import StylePreview from '@/components/StylePreview.vue'
import DevPanel from '@/components/DevPanel.vue'
import { useAppStore } from '@/stores/app'
import { useConfigStore } from '@/stores/config'
import { api } from '@/api/pywebview'
import type { ConfigData } from '@/types'

defineOptions({ name: 'Config' })

const appStore = useAppStore()
const configStore = useConfigStore()

const DEFAULT_STYLE = {
  trace_line_color: '#000000',
  trace_line_width: 0.85,
  hull_line_color: '#1565C0',
  hull_fill_alpha: 0.08,
  circle_window_line_color: '#E65100',
  circle_window_fill_alpha: 0.08,
  rose_bar_color: '#C94C4C',
  rose_bar_edge: '#7A1F1F',
  rose_grid_color: '#d9d9d9',
  title_font_size: 10.4,
  node_style: 'default',
}

const form = ref<ConfigData>({})
const styleConfig = ref<ConfigData>({ ...DEFAULT_STYLE })
const previewTrigger = ref(0)
const fileInputRef = ref<HTMLInputElement>()

async function reloadConfig() {
  try {
    const cfg = await configStore.loadConfig()
    form.value = { ...(cfg as Record<string, any>) }
    if (cfg.style && typeof cfg.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...(cfg.style as Record<string, any>) }
    }
    if (cfg.input_dir) appStore.inputDir = cfg.input_dir as string
    if (cfg.output_dir) appStore.outputDir = cfg.output_dir as string
    msg.success('配置已重新加载')
  } catch (e) {
    msg.error('重新加载配置失败')
  }
}

// 保持 loadConfig 别名供其他地方（如 DevPanel 回调）使用
const loadConfig = reloadConfig

async function saveStyleConfig() {
  try {
    const payload = {
      style: { ...styleConfig.value },
    }
    const saved = (await configStore.saveConfig(payload)) as Record<string, any>
    if (saved.style && typeof saved.style === 'object') {
      styleConfig.value = { ...(saved.style as Record<string, any>) }
    }
    msg.success('样式设置已保存')
  } catch (e) {
    msg.error('保存样式设置失败')
  }
}

async function resetProcessingConfig() {
  try {
    await ElMessageBox.confirm(
      h('div', null, [
        '确定要将处理参数重置为默认值吗？',
        h('div', { class: 'tp-confirm-warning' }, '此操作不可撤销'),
      ]),
      '重置处理设置',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        type: 'warning',
        showClose: false,
        confirmButtonClass: 'tp-confirm-danger-btn',
        customClass: 'tp-confirm-box',
      },
    )
  } catch {
    return
  }
  try {
    const cfg = (await configStore.resetProcessingConfig()) as Record<string, any>
    form.value = { ...cfg }
    if (cfg.input_dir) appStore.inputDir = cfg.input_dir as string
    if (cfg.output_dir) appStore.outputDir = cfg.output_dir as string
    msg.success('处理参数已重置为默认')
  } catch (e) {
    msg.error('重置处理参数失败')
  }
}

async function resetStyleConfig() {
  try {
    await ElMessageBox.confirm(
      h('div', null, [
        '确定要将样式设置重置为默认值吗？',
        h('div', { class: 'tp-confirm-warning' }, '此操作不可撤销'),
      ]),
      '重置样式设置',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        type: 'warning',
        showClose: false,
        confirmButtonClass: 'tp-confirm-danger-btn',
        customClass: 'tp-confirm-box',
      },
    )
  } catch {
    return
  }
  try {
    const cfg = (await configStore.resetStyleConfig()) as Record<string, any>
    styleConfig.value = { ...DEFAULT_STYLE }
    if (cfg.style && typeof cfg.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...(cfg.style as Record<string, any>) }
    }
    previewTrigger.value += 1
    msg.success('样式设置已重置为默认')
  } catch (e) {
    msg.error('重置样式设置失败')
  }
}

async function resetAllConfig() {
  try {
    await ElMessageBox.confirm(
      h('div', null, [
        '确定要恢复所有默认配置吗？此操作将重置全部设置。',
        h('div', { class: 'tp-confirm-warning' }, '此操作不可撤销'),
      ]),
      '重置所有设置',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        type: 'error',
        showClose: false,
        confirmButtonClass: 'tp-confirm-danger-btn',
        customClass: 'tp-confirm-box',
      },
    )
  } catch {
    return
  }
  try {
    const cfg = (await configStore.resetConfig()) as Record<string, any>
    form.value = { ...cfg }
    styleConfig.value = { ...DEFAULT_STYLE }
    if (cfg.style && typeof cfg.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...(cfg.style as Record<string, any>) }
    }
    previewTrigger.value += 1
    if (cfg.input_dir) appStore.inputDir = cfg.input_dir as string
    if (cfg.output_dir) appStore.outputDir = cfg.output_dir as string
    msg.success('已恢复所有默认配置')
  } catch (e) {
    msg.error('重置失败')
  }
}

async function exportJSON() {
  try {
    const folder = await api.browse_folder()
    if (!folder) return
    const jsonStr = JSON.stringify(configStore.config, null, 2)
    await api.export_config_json(folder, jsonStr)
    msg.success(`配置已导出到 ${folder}`)
  } catch (e) {
    msg.error('导出配置失败')
  }
}

function triggerImportJSON() {
  fileInputRef.value?.click()
}

async function importJSON(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const imported = JSON.parse(text)
    const saved = (await configStore.saveConfig(imported)) as Record<string, any>
    form.value = { ...saved }
    if (saved.style && typeof saved.style === 'object') {
      styleConfig.value = { ...DEFAULT_STYLE, ...(saved.style as Record<string, any>) }
      previewTrigger.value += 1
    }
    if (saved.input_dir) appStore.inputDir = saved.input_dir as string
    if (saved.output_dir) appStore.outputDir = saved.output_dir as string
    msg.success(`已导入配置: ${file.name}`)
  } catch (e) {
    msg.error('导入失败：无效的 JSON 文件')
  } finally {
    // 重置 input 以允许重复选择同一文件
    input.value = ''
  }
}

function onStyleChange(val: ConfigData) {
  styleConfig.value = { ...val }
  previewTrigger.value += 1
}

watch(
  () => configStore.config.input_dir as string | undefined,
  (val) => { if (val) appStore.inputDir = val },
)

watch(
  () => configStore.config.output_dir as string | undefined,
  (val) => { if (val) appStore.outputDir = val },
)

onMounted(async () => {
  await loadConfig()
})

// 导出当前表单供外部使用
function getForm() {
  return form.value
}

defineExpose({ getForm })
</script>

<style scoped lang="scss">
.config-view {
  padding: var(--tp-space-5) var(--tp-space-6);
  height: 100%;
  overflow-y: auto;
}

.page-title {
  font-family: var(--tp-font-heading);
  font-size: 22px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin-bottom: var(--tp-space-4);
}

.action-bar {
  display: flex;
  align-items: center;
  gap: var(--tp-space-3);
  margin-top: var(--tp-space-5);
  padding: var(--tp-space-3) var(--tp-space-4);
  flex-wrap: wrap;
}

.action-group {
  display: flex;
  align-items: center;
  gap: var(--tp-space-2);
}

.action-divider {
  width: 1px;
  height: 24px;
  background: var(--tp-border);
}

.action-bar .el-button {
  font-family: var(--tp-font-heading);
}
</style>
