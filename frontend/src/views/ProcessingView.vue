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
      @run="handleRunSingle"
    />

    <!-- 进度面板 -->
    <ProgressPanel
      :running="pipelineStore.running"
      :progress="pipelineStore.progress"
      v-model:parallel="parallel"
      @run="startPipeline"
    />

    <!-- 处理结果列表 -->
    <div v-if="completedResults.length > 0" class="results-panel">
      <h3>处理结果</h3>
      <el-table :data="completedResults" size="small" style="width: 100%">
        <el-table-column prop="outcrop" label="露头" width="80" />
        <el-table-column prop="trace_count" label="迹线数" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '完成' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mean_length" label="平均迹长" width="100">
          <template #default="{ row }">
            {{ row.mean_length ? row.mean_length.toFixed(2) + 'm' : '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="scanline_azimuth" label="走向" width="100">
          <template #default="{ row }">
            {{ row.scanline_azimuth ? row.scanline_azimuth.toFixed(1) + '°' : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'success'"
              size="small"
              type="primary"
              @click="openImageModal(row)"
            >
              打开图片
            </el-button>
          </template>
        </el-table-column>
      </el-table>
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
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import FileList from '@/components/FileList.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import ImageModal from '@/components/ImageModal.vue'
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
})

// 完成的结果列表（实时 + 历史）
const completedResults = ref<PipelineResult[]>([])

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

async function loadHistoryResults() {
  try {
    const results = await api.get_results()
    // 将结果转换为 PipelineResult 格式
    for (const r of results) {
      if (!completedResults.value.find((cr) => cr.outcrop === r.outcrop)) {
        // 尝试获取统计信息补充数据
        try {
          const stats = await api.get_stats(r.outcrop)
          completedResults.value.push({
            outcrop: r.outcrop,
            status: 'success',
            trace_count: stats.trace_count || 0,
            mean_length: stats.mean_trace_length || 0,
            scanline_azimuth: stats.scanline_azimuth || 0,
            excel_path: '',
            raw_plot_path: r.raw_plot || '',
            rotated_plot_path: r.rotated_plot || '',
            rose_plot_path: r.rose_plot || '',
            window_strategy: stats.window_strategy || '',
            area_source: stats.area_source || '',
          })
        } catch {
          completedResults.value.push({
            outcrop: r.outcrop,
            status: 'success',
            trace_count: 0,
            mean_length: 0,
            scanline_azimuth: 0,
            excel_path: '',
            raw_plot_path: r.raw_plot || '',
            rotated_plot_path: r.rotated_plot || '',
            rose_plot_path: r.rose_plot || '',
            window_strategy: '',
            area_source: '',
          })
        }
      }
    }
  } catch (e) {
    console.error('加载历史结果失败', e)
  }
}

function handleSelect(val: TraceFile[]) {
  selectedFiles.value = val
  appStore.selectedFileCount = val.length
}

function handlePreview(row: TraceFile) {
  // 预览数据：可以跳转到数据页
}

function handleRunSingle(row: TraceFile) {
  selectedFiles.value = [row]
  appStore.selectedFileCount = 1
  startPipeline()
}

function openImageModal(result: PipelineResult) {
  modalOutcrop.value = result.outcrop
  modalImages.value = [
    { key: 'raw', title: '原始迹线图', src: result.raw_plot_path },
    { key: 'rotated', title: '旋转迹线图', src: result.rotated_plot_path },
    { key: 'rose', title: '走向玫瑰图', src: result.rose_plot_path },
  ]
  modalVisible.value = true
}

async function startPipeline() {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请至少选择一个文件')
    return
  }
  pipelineStore.reset()
  const targets = selectedFiles.value.map((f) => f.outcrop)
  // 合并本地参数和全局配置
  const config = { ...configStore.config, ...params.value, parallel: parallel.value }
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
          if (evt.result) {
            const existingIndex = completedResults.value.findIndex(
              (r) => r.outcrop === evt.result.outcrop
            )
            if (existingIndex >= 0) {
              completedResults.value[existingIndex] = evt.result
            } else {
              completedResults.value.push(evt.result)
            }
          }
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
  // 加载配置到参数面板
  if (Object.keys(configStore.config).length === 0) {
    try {
      const cfg = await api.get_config()
      configStore.config = { ...cfg }
    } catch (e) {
      console.warn('加载配置失败', e)
    }
  }
  // 将配置中的参数同步到本地
  const cfg = configStore.config
  params.value = {
    export_rose_plot: cfg.export_rose_plot ?? true,
    rose_dpi: cfg.rose_dpi ?? 400,
    rose_bin_width: cfg.rose_bin_width ?? 10,
    trace_dpi: cfg.trace_dpi ?? 300,
    rotated_trace_dpi: cfg.rotated_trace_dpi ?? 600,
    window_strategy: cfg.window_strategy ?? 'auto',
    auto_density_threshold: cfg.auto_density_threshold ?? 5.0,
    tangent_window_count: cfg.tangent_window_count ?? 3,
  }
  await loadFiles()
  await loadHistoryResults()
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
.results-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  margin-top: 16px;
}
.results-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
</style>
