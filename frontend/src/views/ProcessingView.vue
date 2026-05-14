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
import { api } from '@/api/pywebview'

const pipelineStore = usePipelineStore()
const configStore = useConfigStore()

const files = ref<any[]>([])
const selectedFiles = ref<any[]>([])
const parallel = ref(1)
const POLL_INTERVAL = 300

const previewImages = computed(() => {
  const last = pipelineStore.results[pipelineStore.results.length - 1]
  if (!last || !last.result) return []
  const r = last.result
  return [
    {
      key: 'raw',
      title: '原始迹线图',
      src: r.raw_plot_path || '',
    },
    {
      key: 'rotated',
      title: '旋转迹线图',
      src: r.rotated_plot_path || '',
    },
    {
      key: 'rose',
      title: '走向玫瑰图',
      src: r.rose_plot_path || '',
    },
  ]
})

async function loadFiles() {
  try {
    const data = await api.scan_files()
    console.log('[ProcessingView] loadFiles received:', data.length, 'files')
    files.value = data
  } catch (e) {
    ElMessage.error('扫描文件失败')
    console.error('[ProcessingView] loadFiles error:', e)
  }
}

function handleSelect(val: any[]) {
  selectedFiles.value = val
}

function handleView(row: any) {
  if (row.status === 'completed') {
    // 自动触发结果展示
    const fakeEvent = { result: { raw_plot_path: '', rotated_plot_path: '', rose_plot_path: '' } }
    pipelineStore.results.push(fakeEvent)
    // 重新加载实际结果
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
  }
}

function handlePreview(row: any) {
  // 预览数据：可以跳转到数据页
}

function handleRunSingle(row: any) {
  selectedFiles.value = [row]
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
      pipelineStore.progress.total = res.total
      startPolling()
    } else {
      ElMessage.warning(res.message || '启动失败')
    }
  } catch (e) {
    ElMessage.error('启动流水线失败')
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
          break
        case 'complete':
          pipelineStore.running = false
          stopPolling()
          ElMessage.success('处理完成')
          loadFiles()
          break
        case 'error':
          pipelineStore.running = false
          stopPolling()
          ElMessage.error(evt.message)
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
