<template>
  <div class="processing-view">
    <h2 class="page-title">处理</h2>

    <!-- 处理参数面板 -->
    <div class="params-panel">
      <h3>处理参数</h3>
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
        <el-form-item label="圆窗策略">
          <el-select v-model="params.window_strategy" style="width:110px">
            <el-option label="auto" value="auto" />
            <el-option label="tangent" value="tangent" />
            <el-option label="hybrid" value="hybrid" />
            <el-option label="concentric" value="concentric" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="params.window_strategy === 'auto'" label="密度阈值">
          <el-input-number v-model="params.auto_density_threshold" :min="1" :max="20" :step="0.5" style="width:100px" />
        </el-form-item>
        <el-form-item v-if="params.window_strategy === 'tangent'" label="切圆数量">
          <el-input-number v-model="params.tangent_window_count" :min="1" :max="10" style="width:100px" />
        </el-form-item>
      </el-form>
    </div>

    <!-- 文件列表 -->
    <FileList
      :files="files"
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
      v-model:parallel="parallel"
      @run="startPipeline"
    />

    <!-- 处理过程栏 -->
    <div class="process-panel">
      <h3>处理过程</h3>
      <div v-if="currentStatus" class="current-status">
        <el-icon><Loading /></el-icon>
        <span>{{ currentStatus }}</span>
      </div>
      <div class="log-list" ref="logListRef">
        <div
          v-for="(log, idx) in processingLogs"
          :key="idx"
          class="log-item"
          :class="`log-${log.type}`"
        >
          <span class="log-time">[{{ log.time }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <el-empty v-if="processingLogs.length === 0" description="暂无处理记录" />
      </div>
    </div>

    <!-- 后端日志面板 -->
    <el-collapse v-model="activeCollapse" class="backend-log-panel">
      <el-collapse-item title="后端日志" name="backend-log">
        <div class="log-controls">
          <el-select v-model="backendLogLevel" size="small" style="width: 100px" @change="loadBackendLogs">
            <el-option label="ALL" value="ALL" />
            <el-option label="INFO" value="INFO" />
            <el-option label="WARNING" value="WARNING" />
            <el-option label="ERROR" value="ERROR" />
          </el-select>
          <el-select v-model="backendLogTail" size="small" style="width: 100px" @change="loadBackendLogs">
            <el-option label="100 行" :value="100" />
            <el-option label="300 行" :value="300" />
            <el-option label="1000 行" :value="1000" />
          </el-select>
          <el-button size="small" :icon="Refresh" @click="loadBackendLogs">刷新</el-button>
        </div>
        <div class="backend-log-content" v-loading="backendLogLoading">
          <pre v-if="backendLogs.length">{{ backendLogs.join('\n') }}</pre>
          <el-empty v-else description="暂无日志" />
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 图片模态窗口 -->
    <ImageModal
      v-model:visible="modalVisible"
      :outcrop="modalOutcrop"
      :images="modalImages"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading, Refresh } from '@element-plus/icons-vue'
import FileList from '@/components/FileList.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import ImageModal from '@/components/ImageModal.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useConfigStore } from '@/stores/config'
import { useAppStore } from '@/stores/app'
import { api } from '@/api/pywebview'
import type { TraceFile, PipelineResult } from '@/types'

const router = useRouter()
const pipelineStore = usePipelineStore()
const configStore = useConfigStore()
const appStore = useAppStore()

const files = ref<TraceFile[]>([])
const selectedFiles = ref<TraceFile[]>([])
const parallel = ref(1)
const POLL_INTERVAL = 300

// 处理参数（本地状态，默认从配置加载）
const params = ref({
  export_rose_plot: true,
  rose_dpi: 400,
  rose_bin_width: 10,
  trace_dpi: 300,
  rotated_trace_dpi: 600,
  window_strategy: 'auto',
  auto_density_threshold: 5.0,
  tangent_window_count: 3,
  enable_node_recognition: true,
})

// 处理过程日志
interface ProcessLog {
  type: 'info' | 'success' | 'error'
  time: string
  message: string
}
const processingLogs = ref<ProcessLog[]>([])
const currentStatus = ref('')
const logListRef = ref<HTMLDivElement>()
const MAX_LOGS = 50
const startTime = ref(0)

// 后端日志面板
const activeCollapse = ref<string[]>([])
const backendLogLevel = ref('ALL')
const backendLogTail = ref(100)
const backendLogs = ref<string[]>([])
const backendLogLoading = ref(false)

async function loadBackendLogs() {
  backendLogLoading.value = true
  try {
    const lines = await api.get_logs(backendLogTail.value, backendLogLevel.value)
    backendLogs.value = lines || []
  } catch (e) {
    console.warn('加载后端日志失败', e)
  } finally {
    backendLogLoading.value = false
  }
}

function addLog(type: ProcessLog['type'], message: string) {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  processingLogs.value.push({ type, time, message })
  if (processingLogs.value.length > MAX_LOGS) {
    processingLogs.value = processingLogs.value.slice(-MAX_LOGS)
  }
  nextTick(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  })
}

// 监听全局配置变化，自动同步到处理参数
watch(() => configStore.config, (newCfg) => {
  if (!newCfg || Object.keys(newCfg).length === 0) return
  params.value = {
    export_rose_plot: newCfg.export_rose_plot ?? true,
    rose_dpi: newCfg.rose_dpi ?? 400,
    rose_bin_width: newCfg.rose_bin_width ?? 10,
    trace_dpi: newCfg.trace_dpi ?? 300,
    rotated_trace_dpi: newCfg.rotated_trace_dpi ?? 600,
    window_strategy: newCfg.window_strategy ?? 'auto',
    auto_density_threshold: newCfg.auto_density_threshold ?? 5.0,
    tangent_window_count: newCfg.tangent_window_count ?? 3,
    enable_node_recognition: newCfg.enable_node_recognition ?? true,
  }
}, { deep: true })

// 模态窗口状态
const modalVisible = ref(false)
const modalOutcrop = ref('')
const modalImages = ref<Array<{ key: string; title: string; src: string }>>([])

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
    const all = await api.get_results()
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
      ElMessage.warning('未找到该露头的处理结果图片')
    }
  } catch (e) {
    ElMessage.error('获取图片列表失败')
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

async function startPipeline() {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请至少选择一个文件')
    return
  }
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
  const runConfig = { ...configStore.config, ...params.value }
  addLog('info', `运行参数: 玫瑰图=${params.value.export_rose_plot ? '是' : '否'}, 节点识别=${params.value.enable_node_recognition ? '是' : '否'}, 玫瑰DPI=${params.value.rose_dpi}, 分箱=${params.value.rose_bin_width}°, 迹线DPI=${params.value.trace_dpi}, 策略=${params.value.window_strategy}`)

  try {
    // 先保存配置，使 config.json 与流水线实际参数一致
    await configStore.saveConfig(runConfig)

    // 再启动流水线（parallel 作为本次运行 UI 参数，不写入 config.json）
    const res = await api.run_pipeline(targets, { ...runConfig, parallel: parallel.value })

    if (res.status === 'started') {
      pipelineStore.running = true
      appStore.pipelineStatus = 'running'
      pipelineStore.progress.total = res.total
      startPolling()
      appStore.updateLastOperation('启动流水线')
    } else if (res.status === 'error') {
      addLog('error', `启动失败: ${res.message || '配置校验错误'}`)
      ElMessage.error(res.message || '启动失败')
      appStore.pipelineStatus = 'error'
    } else {
      addLog('error', `启动失败: ${res.message || '未知错误'}`)
      ElMessage.warning(res.message || '启动失败')
    }
  } catch (e) {
    addLog('error', '启动流水线失败')
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
          pipelineStore.results.push(evt)
          if (evt.result) {
            if (evt.result.status === 'success') {
              let info = `${evt.result.outcrop} 处理完成 — 迹线数=${evt.result.trace_count}, 走向=${evt.result.scanline_azimuth.toFixed(1)}°, 策略=${evt.result.window_strategy || 'auto'}`
              if (params.value.enable_node_recognition && evt.result.node_count != null) {
                info += `, 节点=${evt.result.node_count}(X${evt.result.node_x_count ?? 0}/Y${evt.result.node_y_count ?? 0}/I${evt.result.node_i_count ?? 0})`
              }
              addLog('success', info)
            } else {
              addLog('error', `${evt.result.outcrop} 处理失败：${evt.result.error || '未知错误'}`)
            }
            // 更新文件列表中对应文件的状态
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
          addLog('success', `全部处理完成 — 总耗时 ${duration}s`)
          currentStatus.value = ''
          ElMessage.success(`处理完成（${duration}s）`)
          appStore.updateLastOperation('处理完成')
          loadFiles()
          loadBackendLogs()
          break
        }
        case 'error': {
          const duration = ((Date.now() - startTime.value) / 1000).toFixed(1)
          pipelineStore.running = false
          appStore.pipelineStatus = 'error'
          stopPolling()
          addLog('error', `处理出错：${evt.message || '未知错误'} — 已运行 ${duration}s`)
          currentStatus.value = ''
          ElMessage.error(evt.message)
          appStore.updateLastOperation('处理出错')
          loadBackendLogs()
          break
        }
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
      export_rose_plot: cfg.export_rose_plot ?? true,
      rose_dpi: cfg.rose_dpi ?? 400,
      rose_bin_width: cfg.rose_bin_width ?? 10,
      trace_dpi: cfg.trace_dpi ?? 300,
      rotated_trace_dpi: cfg.rotated_trace_dpi ?? 600,
      window_strategy: cfg.window_strategy ?? 'auto',
      auto_density_threshold: cfg.auto_density_threshold ?? 5.0,
      tangent_window_count: cfg.tangent_window_count ?? 3,
      enable_node_recognition: cfg.enable_node_recognition ?? true,
    }
  }
  await loadFiles()
  await loadBackendLogs()
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
.params-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}
.params-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
.process-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  margin-top: 16px;
}
.process-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
.current-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #409eff;
}
.current-status .el-icon {
  animation: rotating 2s linear infinite;
}
@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.log-list {
  max-height: 300px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.8;
}
.log-item {
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
}
.log-item:last-child {
  margin-bottom: 0;
}
.log-time {
  color: #909399;
  margin-right: 8px;
  font-family: monospace;
}
.log-info {
  background: #f4f4f5;
  color: #606266;
}
.log-success {
  background: #f0f9eb;
  color: #67c23a;
}
.log-error {
  background: #fef0f0;
  color: #f56c6c;
}
.backend-log-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  margin-top: 16px;
}
.backend-log-panel :deep(.el-collapse-item__header) {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
}
.log-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}
.backend-log-content {
  max-height: 400px;
  overflow-y: auto;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
}
.backend-log-content pre {
  margin: 0;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  color: #303133;
}
</style>