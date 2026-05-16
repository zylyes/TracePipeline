<template>
  <div class="config-view">
    <h2 class="page-title">配置</h2>
    <ConfigForm v-model="form" :style-config="styleConfig" @style-change="onStyleChange" @save-style="saveStyleConfig" @reset-style="resetStyleConfig" />
    <StylePreview :style-config="styleConfig" @save-style="saveStyleConfig" @reset-style="resetStyleConfig" />
    <DevPanel v-show="appStore.isDevMode" @saved="loadConfig" @reset="loadConfig" />

    <div class="action-bar">
      <el-button :icon="Refresh" @click="reloadConfig">重新加载配置</el-button>
      <el-button :icon="Upload" @click="triggerImportJSON">导入 JSON</el-button>
      <el-button :icon="Download" @click="exportJSON">导出 JSON</el-button>
      <el-button :icon="Setting" @click="resetProcessingConfig">重置处理设置</el-button>
      <el-button :icon="RefreshRight" @click="resetAllConfig">重置所有设置</el-button>
      <input ref="fileInputRef" type="file" accept=".json" style="display: none" @change="importJSON" />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
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

const form = ref<ConfigData>({})
const styleConfig = ref<ConfigData>({
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
})
const fileInputRef = ref<HTMLInputElement>()

async function reloadConfig() {
  try {
    const cfg = await configStore.loadConfig()
    form.value = { ...cfg }
    if (cfg.style && typeof cfg.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...cfg.style }
    }
    if (cfg.input_dir) appStore.inputDir = cfg.input_dir
    if (cfg.output_dir) appStore.outputDir = cfg.output_dir
    ElMessage.success('配置已重新加载')
  } catch (e) {
    ElMessage.error('重新加载配置失败')
  }
}

// 保持 loadConfig 别名供其他地方（如 DevPanel 回调）使用
const loadConfig = reloadConfig

async function saveStyleConfig() {
  try {
    const payload = {
      style: { ...styleConfig.value },
    }
    const saved = await configStore.saveConfig(payload)
    if (saved.style && typeof saved.style === 'object') {
      styleConfig.value = { ...saved.style }
    }
    ElMessage.success('样式设置已保存')
  } catch (e) {
    ElMessage.error('保存样式设置失败')
  }
}

async function resetProcessingConfig() {
  try {
    const cfg = await configStore.resetProcessingConfig()
    form.value = { ...cfg }
    // 样式保持不变
    // 同步侧边栏路径
    if (cfg.input_dir) appStore.inputDir = cfg.input_dir
    if (cfg.output_dir) appStore.outputDir = cfg.output_dir
    ElMessage.success('处理参数已重置为默认')
  } catch (e) {
    ElMessage.error('重置处理参数失败')
  }
}

async function resetStyleConfig() {
  try {
    const cfg = await configStore.resetStyleConfig()
    // 强制用本地默认值覆盖，避免空对象导致组件不同步
    styleConfig.value = {
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
    if (cfg.style && typeof cfg.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...cfg.style }
    }
    ElMessage.success('样式设置已重置为默认')
  } catch (e) {
    ElMessage.error('重置样式设置失败')
  }
}

async function resetAllConfig() {
  try {
    const cfg = await configStore.resetConfig()
    form.value = { ...cfg }
    // 强制用本地默认值覆盖，避免空对象导致组件不同步
    styleConfig.value = {
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
    if (cfg.style && typeof cfg.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...cfg.style }
    }
    // 同步侧边栏路径
    if (cfg.input_dir) appStore.inputDir = cfg.input_dir
    if (cfg.output_dir) appStore.outputDir = cfg.output_dir
    ElMessage.success('已恢复所有默认配置')
  } catch (e) {
    ElMessage.error('重置失败')
  }
}

async function exportJSON() {
  try {
    const folder = await api.browse_folder()
    if (!folder) return
    const jsonStr = JSON.stringify(configStore.config, null, 2)
    await api.export_config_json(folder, jsonStr)
    ElMessage.success(`配置已导出到 ${folder}`)
  } catch (e) {
    ElMessage.error('导出配置失败')
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
    form.value = { ...imported }
    if (imported.style && typeof imported.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...imported.style }
    }
    if (imported.input_dir) appStore.inputDir = imported.input_dir
    if (imported.output_dir) appStore.outputDir = imported.output_dir
    ElMessage.success(`已导入配置: ${file.name}`)
  } catch (e) {
    ElMessage.error('导入失败：无效的 JSON 文件')
  } finally {
    // 重置 input 以允许重复选择同一文件
    input.value = ''
  }
}

function onStyleChange(val: ConfigData) {
  styleConfig.value = { ...val }
}

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
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 16px;
}
.action-bar {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
</style>
