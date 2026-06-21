<template>
  <div class="processing-view">
    <h2 class="page-title">处理</h2>

    <!-- 处理参数面板 -->
    <div class="params-panel tp-card tp-neon-edge">
      <div class="params-header">
        <div class="params-header-left">
          <div class="params-icon">
            <el-icon :size="16"><Setting /></el-icon>
          </div>
          <h3>处理参数</h3>
        </div>
        <el-button type="primary" size="small" :icon="Document" @click="saveParams" class="save-btn">保存参数</el-button>
      </div>
      <el-form :model="params" inline size="small">
        <el-form-item label="导出玫瑰图">
          <el-switch v-model="params.export_rose_plot" />
        </el-form-item>
        <el-form-item label="启用节点识别">
          <el-switch v-model="params.enable_node_recognition" />
        </el-form-item>
        <el-form-item label="玫瑰图 DPI">
          <el-select v-model="params.rose_dpi" style="width:90px">
            <el-option v-for="d in [200,300,400,600]" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="分箱宽度">
          <el-select v-model="params.rose_bin_width" style="width:90px">
            <el-option v-for="b in [5,10,15,20,30]" :key="b" :label="b + '°'" :value="b" />
          </el-select>
        </el-form-item>
        <el-form-item label="原始图 DPI">
          <el-select v-model="params.trace_dpi" style="width:90px">
            <el-option v-for="d in [150,200,300,400,600]" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="旋转图 DPI">
          <el-select v-model="params.rotated_trace_dpi" style="width:90px">
            <el-option v-for="d in [300,400,600,800]" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- 文件列表 -->
    <FileList
      :files="files"
      :loading="filesLoading"
      @refresh="loadFiles"
      @select="handleSelect"
      @preview="handlePreview"
      @open-image="handleOpenImage"
      @run="handleRunSingle"
    />

    <!-- 进度面板 -->
    <ProgressPanel
      :running="pipelineStore.running"
      :progress="pipelineStore.progress"
      v-model:parallel="parallelWorkers"
      @run="startPipeline"
    />

    <!-- 处理过程栏 -->
    <div class="process-panel tp-card tp-neon-edge" :class="{ 'is-live': pipelineStore.running, 'is-error': appStore.pipelineStatus === 'error' }">
      <div class="process-header">
        <div class="process-header-left">
          <div class="process-icon">
            <el-icon :size="16"><List /></el-icon>
          </div>
          <h3>处理过程</h3>
        </div>
        <span v-if="processingLogs.length > 0" class="log-count">{{ processingLogs.length }} 条记录</span>
      </div>
      <div v-if="currentStatus" class="current-status">
        <el-icon class="tp-rotate"><Loading /></el-icon>
        <span>{{ currentStatus }}</span>
      </div>
      <div class="log-list" ref="logListRef">
        <div
          v-for="(log, idx) in processingLogs"
          :key="idx"
          class="log-item"
          :class="[
            `log-${log.type}`,
            { 'is-final': log.isFinal }
          ]"
        >
          <div class="log-stripe" :class="`stripe-${log.type}`"></div>
          <span class="log-time tp-time">[{{ log.time }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <el-empty v-if="processingLogs.length === 0" description="暂无处理记录" />
      </div>
    </div>

    <!-- 图片模态窗口 -->
    <ImageModal
      v-model:visible="modalVisible"
      :outcrop="modalOutcrop"
      :images="modalImages"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onActivated, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { msg } from '@/utils/message'
import { Loading, Document, Setting, List } from '@element-plus/icons-vue'
import FileList from '@/components/FileList.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import ImageModal from '@/components/ImageModal.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useConfigStore } from '@/stores/config'
import { useAppStore } from '@/stores/app'
import { useCacheStore } from '@/stores/cache'
import { api } from '@/api/pywebview'
import { formatAreaSource } from '@/utils/format'
import type { TraceFile, PipelineResult } from '@/types'

defineOptions({ name: 'Processing' })

const router = useRouter()
const pipelineStore = usePipelineStore()
const configStore = useConfigStore()
const appStore = useAppStore()
const cacheStore = useCacheStore()

const files = ref<TraceFile[]>([])
const selectedFiles = ref<TraceFile[]>([])
const filesLoading = ref(false)
const POLL_INTERVAL = 300

  // 处理参数（本地状态，默认从配置加载）
  const params = ref({
    export_rose_plot: false,
    rose_dpi: 600,
    rose_bin_width: 10,
    trace_dpi: 600,
    rotated_trace_dpi: 600,
    enable_node_recognition: false,
  })

  // 监听开关变化，实时持久化到全局 store（localStorage）
  watch(
    () => [params.value.export_rose_plot, params.value.enable_node_recognition],
    ([rose, node]) => {
      pipelineStore.setLastRunConfig(node, rose)
    },
    { immediate: false }
  )

// 处理过程日志
interface ProcessLog {
  type: 'info' | 'success' | 'error'
  time: string
  message: string
  isFinal?: boolean
}
const processingLogs = ref<ProcessLog[]>([])
const currentStatus = ref('')
const logListRef = ref<HTMLDivElement>()
const MAX_LOGS = 50
const startTime = ref(0)

// 并行进程数（双向绑定：ProgressPanel 滑块 ↔ configStore.parallel_workers）
const parallelWorkers = ref<number>(0)

// 从 configStore 同步到 parallelWorkers（外部变更如配置加载/重置时生效）
watch(() => configStore.config?.parallel_workers, (val) => {
  if (val !== undefined && val !== null) {
    const num = Number(val)
    if (Number.isFinite(num) && num !== parallelWorkers.value) {
      parallelWorkers.value = num
    }
  }
}, { immediate: true })

// 从 parallelWorkers 同步到 configStore（用户拖动滑块时写入）
watch(parallelWorkers, (val) => {
  if (configStore.config && configStore.config.parallel_workers !== val) {
    configStore.config.parallel_workers = val
  }
})

function addLog(type: ProcessLog['type'], message: string, isFinal = false) {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  processingLogs.value.push({ type, time, message, isFinal })
  if (processingLogs.value.length > MAX_LOGS) {
    processingLogs.value = processingLogs.value.slice(-MAX_LOGS)
  }
  nextTick(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  })
}

// 监听全局配置变化，自动同步到处理参数（排除本地保存触发的更新）
let syncingParams = false
watch(
  () => [
    configStore.config?.export_rose_plot,
    configStore.config?.rose_dpi,
    configStore.config?.rose_bin_width,
    configStore.config?.trace_dpi,
    configStore.config?.rotated_trace_dpi,
    configStore.config?.enable_node_recognition,
  ],
  ([export_rose_plot, rose_dpi, rose_bin_width, trace_dpi, rotated_trace_dpi, enable_node_recognition]) => {
    if (syncingParams) return
    params.value = {
      export_rose_plot: export_rose_plot ?? false,
      rose_dpi: rose_dpi ?? 600,
      rose_bin_width: rose_bin_width ?? 10,
      trace_dpi: trace_dpi ?? 600,
      rotated_trace_dpi: rotated_trace_dpi ?? 600,
      enable_node_recognition: enable_node_recognition ?? false,
    }
  },
)

// 模态窗口状态
const modalVisible = ref(false)
const modalOutcrop = ref('')
const modalImages = ref<Array<{ key: string; title: string; src: string }>>([])
let isLoadingFiles = false

async function loadFiles(force = false) {
  if (isLoadingFiles) {
    return
  }
  isLoadingFiles = true
  filesLoading.value = true
  try {
    if (force) {
      cacheStore.invalidateScan()
    }
    // 优先使用缓存，但仅当非强制刷新且缓存有效时
    let data = (!force) ? cacheStore.getScan() : null
    if (!data) {
      data = (await api.scan_files(force)) as any[]
      cacheStore.setScan(data)
    }
    files.value = (data as any[]).map((f: any) => ({
      stem: f.stem,
      outcrop: f.outcrop,
      path: f.path,
      status: f.status === 'completed' ? 'completed' : 'pending',
    })) as TraceFile[]
  } catch (e: unknown) {
    const errMsg = (e instanceof Error ? e.message : String(e)) || '未知错误'
    msg.error(`扫描文件失败: ${errMsg}`)
    console.error('[ProcessingView] loadFiles error:', e)
    // 失败后延迟 1s 自动重试一次
    setTimeout(() => {
      loadFiles(true).catch((e: unknown) => { console.error('[ProcessingView] 自动重试失败:', e) })
    }, 1000)
  } finally {
    isLoadingFiles = false
    filesLoading.value = false
  }
}

function handleSelect(val: TraceFile[]) {
  selectedFiles.value = val
  appStore.selectedFileCount = val.length
}

function handlePreview(row: TraceFile) {
  router.push({ path: '/data', query: { outcrop: row.outcrop, source: 'input' } })
}

async function handleOpenImage(row: TraceFile) {
  // 优先从 pipelineStore 缓存中查找
  const cached = pipelineStore.results.find(
    (r: any) => r.outcrop === row.outcrop && r.status === 'success'
  )
  if (cached) {
    openImageModal(cached)
    return
  }

  // 缓存未命中，扫描 output 目录
  try {
    const all = (await api.get_results()) as any[]
    const found = all.find((r: any) => r.outcrop === row.outcrop)
    if (found) {
      const result: PipelineResult = {
        outcrop: found.outcrop,
        status: 'success',
        trace_count: 0,
        mean_length: 0,
        scanline_azimuth: 0,
        excel_path: '',
        raw_plot: found.raw_plot || '',
        rotated_plot: found.rotated_plot || '',
        rose_plot: found.rose_plot || '',
        window_strategy: '',
        area_source: '',
      }
      openImageModal(result)
    } else {
      msg.warning('未找到该露头的处理结果图片')
    }
  } catch (e) {
    msg.error('获取图片列表失败')
    console.error(e)
  }
}

function handleRunSingle(row: TraceFile) {
  selectedFiles.value = [row]
  appStore.selectedFileCount = 1
  startPipeline()
}

function openImageModal(result: PipelineResult) {
  modalOutcrop.value = result.outcrop
  const images = [
    { key: 'raw', title: '原始迹线图', src: result.raw_plot },
    { key: 'rotated', title: '旋转迹线图', src: result.rotated_plot },
  ]
  if (params.value.export_rose_plot) {
    images.push({ key: 'rose', title: '走向玫瑰图', src: result.rose_plot })
  }
  modalImages.value = images
  modalVisible.value = true
}

async function saveParams() {
  syncingParams = true
  try {
    const payload = {
      export_rose_plot: params.value.export_rose_plot,
      rose_dpi: params.value.rose_dpi,
      rose_bin_width: params.value.rose_bin_width,
      trace_dpi: params.value.trace_dpi,
      rotated_trace_dpi: params.value.rotated_trace_dpi,
      enable_node_recognition: params.value.enable_node_recognition,
    }
    await configStore.saveConfig(payload)
    msg.success('处理参数已保存')
  } catch (e) {
    msg.error('保存处理参数失败')
  } finally {
    syncingParams = false
  }
}

async function startPipeline() {
  if (pipelineStore.running) return
  if (selectedFiles.value.length === 0) {
    msg.warning('请至少选择一个文件')
    return
  }
  stopPolling()
  pipelineStore.reset()
  processingLogs.value = []
  currentStatus.value = ''
  startTime.value = Date.now()
  const targets = selectedFiles.value.map((f) => f.outcrop)

  // 保存最近一次运行配置到全局状态（用于控制其他页面显示）
  pipelineStore.setLastRunConfig(
    params.value.enable_node_recognition,
    params.value.export_rose_plot
  )

  // 合并本地参数和全局配置，先保存再启动，保证后端事实源一致
  const runConfig: Record<string, any> = { ...configStore.config, ...params.value }
  addLog('info', `运行参数: 玫瑰图=${params.value.export_rose_plot ? '是' : '否'}, 节点识别=${params.value.enable_node_recognition ? '是' : '否'}, 玫瑰DPI=${params.value.rose_dpi}, 分箱=${params.value.rose_bin_width}°, 迹线DPI=${params.value.trace_dpi}, 旋转图DPI=${params.value.rotated_trace_dpi}`)

  try {
    // 先保存配置，使 config.json 与流水线实际参数一致
    await configStore.saveConfig(runConfig)

    // 再启动流水线
    const res = (await api.run_pipeline(targets, runConfig)) as { status: string; total?: number; message?: string }

    if (res.status === 'started') {
      pipelineStore.running = true
      appStore.pipelineStatus = 'running'
      pipelineStore.progress.total = res.total ?? 1
      startPolling()
      appStore.updateLastOperation('启动流水线')
    } else if (res.status === 'error') {
      addLog('error', `启动失败: ${res.message || '配置校验错误'}`)
      msg.error(res.message || '启动失败')
      appStore.pipelineStatus = 'error'
    } else {
      addLog('error', `启动失败: ${res.message || '未知错误'}`)
      msg.warning(res.message || '启动失败')
    }
  } catch (e) {
    addLog('error', '启动流水线失败')
    msg.error('启动流水线失败')
    appStore.pipelineStatus = 'error'
  }
}

let pollTimer: number | null = null
let pollStopped = true
let pollErrorCount = 0
const MAX_POLL_ERRORS = 5

function startPolling() {
  stopPolling()
  pollStopped = false
  pollErrorCount = 0
  scheduleNextPoll(0)
}

function scheduleNextPoll(delay: number) {
  if (pollStopped) return
  pollTimer = window.setTimeout(runPollTick, delay)
}

async function runPollTick() {
  if (pollStopped) return
  try {
    let evt
    while (!pollStopped && (evt = await api.poll_progress())) {
      handlePollEvent(evt)
    }
    pollErrorCount = 0
  } catch (e) {
    pollErrorCount++
    if (pollErrorCount >= MAX_POLL_ERRORS) {
      stopPolling()
      pipelineStore.running = false
      appStore.pipelineStatus = 'error'
      addLog('error', `轮询失败（连续 ${MAX_POLL_ERRORS} 次），已停止`)
      msg.error('与后端通信失败，请检查后端是否仍在运行')
      return
    }
  }
  scheduleNextPoll(POLL_INTERVAL)
}

function handlePollEvent(evt: any) {
  switch (evt.type) {
    case 'start':
      pipelineStore.progress.total = evt.total
      addLog('info', `开始处理，共 ${evt.total} 个文件`)
      currentStatus.value = ''
      break
    case 'progress':
      pipelineStore.progress = {
        current: evt.current,
        total: evt.total,
        filename: evt.filename,
        message: evt.message,
      }
      currentStatus.value = `正在处理：${evt.filename}（${evt.current}/${evt.total}）`
      break
    case 'file_complete':
      if (evt.result) pipelineStore.results.push(evt.result)
      if (evt.result) {
        if (evt.result.status === 'success') {
          let info = `${evt.result.outcrop} 处理完成 — 迹线数=${evt.result.trace_count}, 测线走向=${evt.result.scanline_azimuth.toFixed(1)}°, 采用策略=${formatAreaSource(evt.result.area_source)}`
          if (params.value.enable_node_recognition && evt.result.node_count != null) {
            info += `, 节点=${evt.result.node_count}(X${evt.result.node_x_count ?? 0}/Y${evt.result.node_y_count ?? 0}/I${evt.result.node_i_count ?? 0})`
          }
          addLog('success', info)
        } else {
          const errType = evt.result.error_type || ''
          let errHint = ''
          if (errType === 'PermissionError') {
            errHint = '文件被占用或权限不足，请关闭已打开的输出文件（如 Excel/WPS）后重试'
          } else if (errType === 'FileNotFoundError') {
            errHint = '输入文件不存在，请检查文件路径'
          }
          const errDetail = errHint ? `${errHint}` : (evt.result.error || '未知错误')
          addLog('error', `${evt.result.outcrop} 处理失败：${errDetail}`)
          if (errType === 'PermissionError') {
            msg.warning(`${evt.result.outcrop} 处理失败：${errHint}`, 3000)
          } else if (errType === 'FileNotFoundError') {
            msg.warning(`${evt.result.outcrop} 处理失败：${errHint}`, 3000)
          }
        }
        const fileIdx = files.value.findIndex((f) => f.outcrop === evt.result.outcrop)
        if (fileIdx >= 0) {
          files.value[fileIdx].status = evt.result.status === 'success' ? 'completed' : 'error'
        }
      }
      appStore.updateLastOperation(`${evt.filename} 完成`)
      break
    case 'complete': {
      const duration = ((Date.now() - startTime.value) / 1000).toFixed(1)
      pipelineStore.running = false
      appStore.pipelineStatus = 'completed'
      stopPolling()
      addLog('success', `全部处理完成 — 总耗时 ${duration}s`, true)
      currentStatus.value = ''
      msg.success(`处理完成（${duration}s）`)
      appStore.updateLastOperation('处理完成')
      // 处理完成后使所有数据缓存失效，确保其他页面刷新时获取最新结果
      cacheStore.invalidateAll()
      loadFiles(true)
      break
    }
    case 'error': {
      const duration = ((Date.now() - startTime.value) / 1000).toFixed(1)
      pipelineStore.running = false
      appStore.pipelineStatus = 'error'
      stopPolling()
      addLog('error', `处理出错：${evt.message || '未知错误'} — 已运行 ${duration}s`)
      currentStatus.value = ''
      msg.error(evt.message)
      appStore.updateLastOperation('处理出错')
      break
    }
  }
}

function stopPolling() {
  pollStopped = true
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  // 若上次运行已结束，清空进度与日志，避免切换回来后仍显示旧状态
  if (!pipelineStore.running && pipelineStore.progress.total > 0 && pipelineStore.progress.current >= pipelineStore.progress.total) {
    pipelineStore.reset()
    processingLogs.value = []
    currentStatus.value = ''
  }

  // 无条件从后端加载最新配置，确保参数面板始终显示正确值
  try {
    await configStore.loadConfig()
  } catch (e) {
    console.warn('加载配置失败', e)
  }
  // 将配置中的参数同步到本地
  const cfg = configStore.config
  if (cfg && Object.keys(cfg).length > 0) {
    params.value = {
      export_rose_plot: cfg.export_rose_plot ?? false,
      rose_dpi: cfg.rose_dpi ?? 600,
      rose_bin_width: cfg.rose_bin_width ?? 10,
      trace_dpi: cfg.trace_dpi ?? 600,
      rotated_trace_dpi: cfg.rotated_trace_dpi ?? 600,
      enable_node_recognition: cfg.enable_node_recognition ?? false,
    }
  }

  // 将当前参数同步到 pipelineStore，确保 UI 显隐与设置一致
  pipelineStore.setLastRunConfig(params.value.enable_node_recognition, params.value.export_rose_plot)

  await loadFiles(false)
})

// KeepAlive 激活时只在缓存过期或本地列表为空时刷新，避免首次激活重复扫描。
onActivated(() => {
  if (!cacheStore.isScanValid) {
    loadFiles(true).catch((e: unknown) => { console.error('[ProcessingView] keepAlive刷新失败:', e) })
  } else if (files.value.length === 0) {
    loadFiles(false).catch((e: unknown) => { console.error('[ProcessingView] keepAlive首次加载失败:', e) })
  }
})

// 输入/输出目录变更后自动刷新文件列表
watch(
  () => [configStore.config.input_dir, configStore.config.output_dir],
  () => {
    cacheStore.invalidateScan()
    loadFiles(true).catch((e: unknown) => { console.error('[ProcessingView] 目录变更刷新失败:', e) })
  },
)

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.processing-view {
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

/* 参数面板 */
.params-panel {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-bottom: var(--tp-space-4);
}

.params-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--tp-space-4);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}

.params-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.params-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-info-bg);
  color: var(--tp-info);
}

.params-panel h3 {
  font-family: var(--tp-font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0;
}

.save-btn {
  font-family: var(--tp-font-heading);
}

/* 处理过程面板 */
.process-panel {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-top: var(--tp-space-4);
  transition: box-shadow 0.3s ease;
}

.process-panel.is-live {
  box-shadow: var(--tp-shadow-md), var(--tp-glow-emerald-sm);
}

.process-panel.is-error {
  animation: tp-border-glow-danger 1s infinite alternate;
}

@keyframes tp-border-glow-danger {
  0% { box-shadow: 0 0 0 1px var(--tp-danger-border); }
  100% { box-shadow: 0 0 12px var(--tp-glow-danger), 0 0 0 1px rgba(239, 68, 68, 0.4); }
}

.process-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}

.process-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.process-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-success-bg);
  color: var(--tp-success);
}

.process-panel h3 {
  font-family: var(--tp-font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0;
}

.log-count {
  font-size: 13px;
  color: var(--tp-text-muted);
  font-family: var(--tp-font-data);
}

.current-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background:
    linear-gradient(90deg, rgba(59, 130, 246, 0.13), rgba(56, 189, 248, 0.08)),
    var(--tp-info-light);
  border-radius: var(--tp-radius-md);
  margin-bottom: var(--tp-space-3);
  font-size: 14px;
  color: var(--tp-info);
  border: 1px solid var(--tp-info-bg);
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.12), var(--tp-glow-cyan-sm);
}

.current-status .el-icon {
  color: var(--tp-info);
}

.log-list {
  max-height: 320px;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.7;
}

.log-item {
  position: relative;
  padding: 6px 10px 6px 14px;
  border-radius: var(--tp-radius-sm);
  margin-bottom: 4px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  overflow: hidden;
  animation: logItemIn 0.28s var(--tp-easing-expo) both;
}

.log-item.log-success.is-final {
  animation: logItemIn 0.28s var(--tp-easing-expo) both, tp-success-burst 0.6s ease-out forwards;
}

@keyframes logItemIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.log-item:last-child {
  margin-bottom: 0;
}

.log-stripe {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  border-radius: 0 2px 2px 0;
}

.stripe-info { background: var(--tp-text-muted); }
.stripe-success { background: var(--tp-success); }
.stripe-error { background: var(--tp-danger); }

.log-time {
  color: var(--tp-text-muted);
  margin-right: 4px;
  flex-shrink: 0;
  font-size: 12px;
}

.log-message {
  color: var(--tp-text-secondary);
  word-break: break-word;
}

.log-info {
  background: rgba(238, 240, 244, 0.72);
}

.log-success {
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.12), rgba(209, 250, 229, 0.72));
}

.log-success .log-message {
  color: var(--tp-success);
}

.log-error {
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.12), rgba(254, 226, 226, 0.76));
}

.log-error .log-message {
  color: var(--tp-danger);
}
</style>
