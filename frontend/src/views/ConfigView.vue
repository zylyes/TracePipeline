<template>
  <div class="config-view">
    <h2 class="page-title">配置</h2>
    <ConfigForm v-model="form" :style-config="styleConfig" @style-change="onStyleChange" />
    <StylePreview :style-config="styleConfig" />
    <DevPanel v-if="appStore.isDevMode" :outcrop="selectedOutcrop" />

    <div class="action-bar">
      <el-button type="primary" @click="saveConfig">💾 保存配置</el-button>
      <el-button @click="loadConfig">📂 加载配置</el-button>
      <el-button @click="exportJSON">📤 导出 JSON</el-button>
      <el-button @click="resetConfig">↺ 重置为默认</el-button>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ConfigForm from '@/components/ConfigForm.vue'
import StylePreview from '@/components/StylePreview.vue'
import DevPanel from '@/components/DevPanel.vue'
import { useAppStore } from '@/stores/app'
import { useConfigStore } from '@/stores/config'
import { api } from '@/api/pywebview'

const appStore = useAppStore()
const configStore = useConfigStore()

const form = ref<any>({})
const styleConfig = ref<any>({
  trace_line_color: '#000000',
  trace_line_width: 0.85,
  hull_line_color: '#1565C0',
  hull_fill_alpha: 0.08,
  circle_window_line_color: '#E65100',
  circle_window_fill_alpha: 0.08,
  rose_bar_color: '#C94C4C',
  rose_bar_edge: '#7A1F1F',
  rose_grid_color: '#d9d9d9',
  global_font_size: 8.5,
})
const selectedOutcrop = ref('O76')

async function loadConfig() {
  try {
    const cfg = await api.get_config()
    form.value = { ...cfg }
    configStore.config = { ...cfg }
    if (cfg.style && typeof cfg.style === 'object') {
      styleConfig.value = { ...styleConfig.value, ...cfg.style }
    }
  } catch (e) {
    ElMessage.error('加载配置失败')
  }
}

async function saveConfig() {
  try {
    const payload = { ...form.value, style: { ...styleConfig.value } }
    await api.set_config(payload)
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存配置失败')
  }
}

async function resetConfig() {
  try {
    const cfg = await api.reset_config()
    form.value = { ...cfg }
    ElMessage.success('已恢复默认配置')
  } catch (e) {
    ElMessage.error('重置失败')
  }
}

function exportJSON() {
  const blob = new Blob([JSON.stringify(form.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'config.json'
  a.click()
  URL.revokeObjectURL(url)
}

function onStyleChange(val: any) {
  styleConfig.value = { ...val }
}

onMounted(loadConfig)
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
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
</style>
