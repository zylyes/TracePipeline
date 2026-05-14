<template>
  <div class="processing-view">
    <h2 class="page-title">处理</h2>
    <FileList
      :files="files"
      @refresh="loadFiles"
      @select="handleSelect"
      @view="handleView"
      @preview="handlePreview"
      @run="handleRunSingle"
    />
    <ProgressPanel
      :running="pipelineStore.running"
      :progress="pipelineStore.progress"
      v-model:parallel="parallel"
      @run="startPipeline"
    />
    <ImagePreview :images="previewImages" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import FileList from '@/components/FileList.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import ImagePreview from '@/components/ImagePreview.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useConfigStore } from '@/stores/config'
import { useAppStore } from '@/stores/app'
import { api } from '@/api/pywebview'
import type { TraceFile, PipelineResult } from '@/types'

const pipelineStore = usePipelineStore()
const configStore = useConfigStore()
const appStore = useAppStore()

const files = ref<TraceFile[]>([])
const selectedFiles = ref<TraceFile[]>([])
const parallel = ref(1)
const POLL_INTERVAL = 300

const previewImages = computed(() => {
  // 收集所有已完成结果中的最新图片
  const images: Array<{ key: string; title: string; src: string }> = []
  const seen = new Set<string>()
  
  for (const evt of pipelineStore.results) {
    if (!evt.result) continue
    const r = evt.result as PipelineResult
    if (!seen.has('raw-' + r.outcrop)) {
      images.push({ key: 'raw-' + r.outcrop, title: r.outcrop + ' 原始迹线图', src: r.raw_plot_path || '' })
      seen.add('raw-' + r.outcrop)
    }
    if (!seen.has('rotated-' + r.outcrop)) {
      images.push({ key: 'rotated-' + r.outcrop, title: r.outcrop + ' 旋转迹线图', src: r.rotated_plot_path || '' })
      seen.add('rotated-' + r.outcrop)
    }
    if (!seen.has('rose-' + r.outcrop) && r.rose_plot_path) {
      images.push({ key: 'rose-' + r.outcrop, title: r.outcrop + ' 走向玫瑰图', src: r.rose_plot_path })
      seen.add('rose-' + r.outcrop)
    }
  }
  return images.slice(-6) // 最多显示最近 6 张
})

async function loadFiles() {
  try {
    const data = await api.scan_files()
    files.value = data.map((f: any) => ({
      stem: f.stem,
      outcrop: f.outcrop,
      path: f.path,
      status: f.status === 'completed' ? 'completed' : 'pending',
    })) as TraceFile[]
  } catch (e) {
    ElMessage.error('扫描文件失败')
    console.error('[ProcessingView] loadFiles error:', e)
  }
}

function handleSelect(val: TraceFile[]) {
  selectedFiles.value = val
  appStore.selectedFileCount = val.length
}

function handleView(row: TraceFile) {
  if (row.status === 'completed') {
    loadResults(row.outcrop)
  }
}

async function loadResults(outcrop: string) {
  try {
    const results = await api.get_results()
    const match = results.find((r: any) => r.outcrop === outcrop)
    if (match) {
      pipelineStore.results.push({ result: match })
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载结果失败')
  }
}

function handlePreview(row: TraceFile) {
  // 预览数据：可以跳转到数据页
}

function handleRunSingle(row: TraceFile) {
  selectedFiles.value = [row]
  appStore.selectedFileCount = 1
  startPipeline()
}

async function startPipeline() {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请至少选择一个文件')
    return
  }
  pipelineStore.reset()
  const targets = selectedFiles.value.map(f => f.outcrop)
  const config = { ...configStore.config, parallel: parallel.value }
  try {
    const res = await api.run_pipeline(targets, config)
    if (res.status === 'started') {
      pipelineStore.running = true
      appStore.pipelineStatus = 'running'
      pipelineStore.progress.total = res.total
      startPolling()
      appStore.updateLastOperation('启动流水线')
    } else {
      ElMessage.warning(res.message || '启动失败')
    }
  } catch (e) {
    ElMessage.error('启动流水线失败')
    appStore.pipelineStatus = 'error'
  }
}

function startPolling() {
  pipelineStore.pollTimer = window.setInterval(async () => {
    try {
      const evt = await api.poll_progress()
      if (!evt) return
      switch (evt.type) {
        case 'start':
          pipelineStore.progress.total = evt.total
          break
        case 'progress':
          pipelineStore.progress = {
            current: evt.current,
            total: evt.total,
            filename: evt.filename,
            message: evt.message,
          }
          break
        case 'file_complete':
          pipelineStore.results.push(evt)
          appStore.updateLastOperation(`${evt.filename} 完成`)
          break
        case 'complete':
          pipelineStore.running = false
          appStore.pipelineStatus = 'completed'
          stopPolling()
          ElMessage.success('处理完成')
          appStore.updateLastOperation('处理完成')
          loadFiles()
          break
        case 'error':
          pipelineStore.running = false
          appStore.pipelineStatus = 'error'
          stopPolling()
          ElMessage.error(evt.message)
          appStore.updateLastOperation('处理出错')
          break
      }
    } catch (e) {
      // ignore
    }
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pipelineStore.pollTimer) {
    clearInterval(pipelineStore.pollTimer)
    pipelineStore.pollTimer = null
  }
}

onMounted(async () => {
  // 自动加载配置，确保 configStore 不为空
  if (Object.keys(configStore.config).length === 0) {
    try {
      const cfg = await api.get_config()
      configStore.config = { ...cfg }
    } catch (e) {
      console.warn('加载配置失败', e)
    }
  }
  await loadFiles()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.processing-view {
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
</style>
