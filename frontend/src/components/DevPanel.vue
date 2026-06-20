<template>
  <div class="dev-panel tp-neon-edge">
    <el-collapse v-model="activeNames" @change="onCollapseChange">
      <el-collapse-item title="毕设报告导出" name="report">
        <div v-loading="loading.report" element-loading-text="正在读取已完成露头" class="report-form">
          <el-form label-width="80px" size="small">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="导出范围">
                  <el-radio-group v-model="reportScope">
                    <el-radio-button label="selected">指定露头</el-radio-button>
                    <el-radio-button label="all">全部已处理</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item v-if="reportScope === 'selected'" label="选择露头">
                  <el-select
                    v-model="selectedOutcrops"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="请选择要导出的露头"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="oc in outcropOptions"
                      :key="oc"
                      :label="oc"
                      :value="oc"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item v-if="reportScope === 'all'" label="包含露头">
                  <div class="outcrop-tags">
                    <el-tag v-for="oc in outcropOptions" :key="oc" size="small" class="oc-tag">{{ oc }}</el-tag>
                    <span v-if="outcropOptions.length === 0" class="oc-empty">暂无已完成露头</span>
                  </div>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="报告类型">
                  <el-radio-group v-model="reportType">
                    <el-radio-button label="full">完整报告</el-radio-button>
                    <el-radio-button label="stats">仅统计</el-radio-button>
                    <el-radio-button label="plots">仅图表</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="格式">
                  <el-radio-group v-model="reportFmt">
                    <el-radio-button label="docx">Word</el-radio-button>
                    <el-radio-button label="pdf">PDF</el-radio-button>
                    <el-radio-button label="both">两者</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item class="report-action">
              <el-button type="primary" :loading="reportLoading" @click="generateReport">
                生成并导出报告
              </el-button>
            </el-form-item>
          </el-form>
          <!-- 报告导出进度条 -->
          <div v-if="reportProgressVisible" class="report-progress-area">
            <el-progress
              :percentage="reportProgressPercent"
              :stroke-width="8"
              :status="reportProgressStatus"
              :color="reportProgressColor"
              class="modern-progress"
            />
            <div class="report-progress-message">
              <template v-if="reportProgress.type === 'complete'">
                <el-icon :size="14" style="color: var(--tp-success)"><CircleCheck /></el-icon>
                <span class="tp-success-text">报告已生成</span>
              </template>
              <template v-else-if="reportProgress.type === 'error'">
                <el-icon :size="14" style="color: var(--tp-error)"><WarningFilled /></el-icon>
                <span class="tp-error-text">{{ reportProgress.message || '生成失败' }}</span>
              </template>
              <template v-else>
                <el-icon class="tp-rotate" :size="12" style="color: var(--tp-brand-accent)"><Loading /></el-icon>
                <span>{{ reportProgress.message }}</span>
                <span v-if="reportProgress.total" class="report-progress-batch">
                  ({{ reportProgress.current }} / {{ reportProgress.total }})
                </span>
              </template>
            </div>
          </div>
        </div>
      </el-collapse-item>

      <el-collapse-item title="操作审计日志" name="audit">
        <div class="audit-scroll-container" v-loading="loading.audit" element-loading-text="正在加载审计记录">
          <div class="audit-list">
            <div
              v-for="item in auditLogs"
              :key="item.timestamp"
              class="audit-item"
            >
              <span class="audit-time">{{ item.timestamp }}</span>
              <span class="audit-action">{{ item.action }} — {{ item.result }}</span>
            </div>
            <el-empty v-if="!loading.audit && auditLogs.length === 0" description="暂无审计记录" :image-size="60" />
          </div>
        </div>
      </el-collapse-item>

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
          <el-button size="small" @click="loadBackendLogs">刷新</el-button>
        </div>
        <div class="backend-log-content" v-loading="backendLogLoading" element-loading-text="正在读取后端日志">
          <pre v-if="backendLogs.length">{{ backendLogs.join('\n') }}</pre>
          <el-empty v-else description="暂无日志" />
        </div>
      </el-collapse-item>

      <el-collapse-item title="高级配置" name="advanced">
        <div class="advanced-form">
          <el-form label-width="100px" size="small">
            <div class="adv-section">
              <div class="adv-section-title">圆窗策略</div>
              <el-row :gutter="16">
                <el-col :span="8">
                  <el-form-item label="策略模式">
                    <el-select v-model="advanced.window_strategy" style="width:140px">
                      <el-option label="自动(auto)" value="auto" />
                      <el-option label="切线(tangent)" value="tangent" />
                      <el-option label="混合(hybrid)" value="hybrid" />
                      <el-option label="同心(concentric)" value="concentric" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8" v-if="advanced.window_strategy === 'auto'">
                  <el-form-item label="密度阈值">
                    <el-input-number v-model="advanced.auto_density_threshold" :min="1" :max="20" :step="0.5" style="width:120px" />
                  </el-form-item>
                </el-col>
                <el-col :span="8" v-if="advanced.window_strategy === 'tangent'">
                  <el-form-item label="切圆数量">
                    <el-input-number v-model="advanced.tangent_window_count" :min="1" :max="20" :step="1" style="width:120px" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="最小交点数">
                    <el-input-number v-model="advanced.min_intersections" :min="1" :max="20" style="width:120px" />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>

            <div class="adv-section">
              <div class="adv-section-title">节点识别参数</div>
              <el-row :gutter="16">
                <el-col :span="8">
                  <el-form-item label="节点合并容差">
                    <el-input-number v-model="advanced.node_merge_tolerance" :min="1e-9" :max="1" :step="1e-6" style="width:140px" />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>

            <div class="adv-section">
              <div class="adv-section-title">面积计算参数</div>
              <el-row :gutter="16">
                <el-col :span="8">
                  <el-form-item label="凸包缓冲比">
                    <el-input-number v-model="advanced.hull_buffer_ratio" :min="0" :max="1" :step="0.05" style="width:120px" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="差异阈值">
                    <el-input v-model="advanced.disagreement_threshold" placeholder="auto" style="width:120px" />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </el-form>
          <div class="dev-action-bar">
            <el-button type="primary" size="small" @click="saveDevConfig">保存高级配置</el-button>
            <el-button size="small" @click="resetDevConfig">重置高级配置</el-button>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
import { ElMessageBox } from 'element-plus'
import { CircleCheck, Loading, WarningFilled } from '@element-plus/icons-vue'
import { msg } from '@/utils/message'
import { api } from '@/api/pywebview'
import { useConfigStore } from '@/stores/config'
import { useCacheStore } from '@/stores/cache'
import type { ReportProgress } from '@/types'

const emit = defineEmits<{
  (e: 'saved'): void
  (e: 'reset'): void
}>()

const configStore = useConfigStore()
const cacheStore = useCacheStore()

const activeNames = ref<string[]>([])
const reportScope = ref('selected')
const reportType = ref('full')
	const reportFmt = ref('docx')
	const reportLoading = ref(false)
	// 报告导出进度
	const reportProgressVisible = ref(false)
	const reportProgress = ref<ReportProgress>({ type: 'progress', message: '' })
	let reportPollTimer: number | null = null

	const POLL_INTERVAL = 300

	const reportProgressPercent = computed(() => {
	  const p = reportProgress.value
	  if (p.type === 'complete') return 100
	  if (p.type === 'error') return 100
	  if (p.total && p.current) {
	    return Math.round((p.current / p.total) * 100)
	  }
	  // 基于步骤估算: loading=10%, stats=30%, docx=60%, pdf=90%
	  switch (p.step) {
	    case 'loading': return 10
	    case 'stats': return 30
	    case 'docx': return 60
	    case 'pdf': return 90
	    case 'zip': return 95
	    default: return 0
	  }
	})

	const reportProgressStatus = computed(() => {
	  if (reportProgress.value.type === 'complete') return 'success' as const
	  if (reportProgress.value.type === 'error') return 'exception' as const
	  return undefined
	})

	const reportProgressColor = computed(() => {
	  if (reportProgress.value.type === 'complete') return 'var(--tp-success)'
	  if (reportProgress.value.type === 'error') return 'var(--tp-error)'
	  return 'var(--tp-brand-accent)'
	})

	function startReportProgressPolling() {
	  stopReportProgressPolling()
	  reportPollTimer = window.setTimeout(async function pollTick() {
	    try {
      const evt = (await api.poll_report_progress()) as Record<string, unknown> | null
      if (evt) {
	        reportProgress.value = evt as unknown as ReportProgress
	        if (evt.type === 'complete' || evt.type === 'error') {
	          // Keep progress visible a bit longer to show completion state
	          setTimeout(() => {
	            reportProgressVisible.value = false
	          }, 2000)
	          return
	        }
	      }
	      if (reportPollTimer !== null) {
	        reportPollTimer = window.setTimeout(pollTick, POLL_INTERVAL)
	      }
	    } catch {
	      // ignore poll errors
	      if (reportPollTimer !== null) {
	        reportPollTimer = window.setTimeout(pollTick, POLL_INTERVAL)
	      }
	    }
	  }, POLL_INTERVAL)
	}

	function stopReportProgressPolling() {
	  if (reportPollTimer !== null) {
	    clearTimeout(reportPollTimer)
	    reportPollTimer = null
	  }
	}

	const outcropOptions = ref<string[]>([])
const selectedOutcrops = ref<string[]>([])
const auditLogs = ref<any[]>([])
const advanced = ref({
  window_strategy: 'auto',
  auto_density_threshold: 5.0,
  tangent_window_count: 3,
  min_intersections: 5,
  node_merge_tolerance: 0.01,
  hull_buffer_ratio: 0.25,
  disagreement_threshold: '',
})

const loading = ref({
  report: false,
  audit: false,
  backendLog: false,
})

const loaded = ref({
  report: false,
  audit: false,
  backendLog: false,
})

// 后端日志
const backendLogLevel = ref('ALL')
const backendLogTail = ref(100)
const backendLogs = ref<string[]>([])
const backendLogLoading = ref(false)

async function loadBackendLogs() {
  backendLogLoading.value = true
  try {
    const lines = await api.get_logs(backendLogTail.value, backendLogLevel.value)
    backendLogs.value = lines || []
    loaded.value.backendLog = true
  } catch (e) {
    console.error('[DevPanel] 加载日志失败', e)
    msg.error('加载后台日志失败')
  } finally {
    backendLogLoading.value = false
  }
}

onMounted(async () => {
  try {
    const cfg = await configStore.loadConfig()
    advanced.value.window_strategy = cfg.window_strategy ?? 'auto'
    advanced.value.auto_density_threshold = cfg.auto_density_threshold ?? 5.0
    advanced.value.tangent_window_count = cfg.tangent_window_count ?? 3
    advanced.value.min_intersections = cfg.min_intersections ?? 5
    advanced.value.node_merge_tolerance = cfg.node_merge_tolerance ?? 0.01
  } catch (e) {
    // ignore
  }
  await loadAudit()
})

async function saveDevConfig() {
  try {
    await configStore.saveConfig({
      window_strategy: advanced.value.window_strategy,
      auto_density_threshold: advanced.value.auto_density_threshold,
      tangent_window_count: advanced.value.tangent_window_count,
      min_intersections: advanced.value.min_intersections,
      node_merge_tolerance: advanced.value.node_merge_tolerance,
    })
    msg.success('高级配置已保存')
    emit('saved')
  } catch (e) {
    msg.error('保存高级配置失败')
  }
}

async function resetDevConfig() {
  try {
    await ElMessageBox.confirm(
      '确定要将高级配置重置为默认值吗？<div class="tp-confirm-warning">此操作不可撤销</div>',
      '重置高级配置',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true,
        showClose: false,
        confirmButtonClass: 'tp-confirm-danger-btn',
        customClass: 'tp-confirm-box',
      },
    )
  } catch {
    return
  }
  advanced.value = {
    window_strategy: 'auto',
    auto_density_threshold: 5.0,
    tangent_window_count: 3,
    min_intersections: 5,
    node_merge_tolerance: 0.01,
    hull_buffer_ratio: 0.25,
    disagreement_threshold: '',
  }
  try {
    await configStore.saveConfig({
      window_strategy: advanced.value.window_strategy,
      auto_density_threshold: advanced.value.auto_density_threshold,
      tangent_window_count: advanced.value.tangent_window_count,
      min_intersections: advanced.value.min_intersections,
      node_merge_tolerance: advanced.value.node_merge_tolerance,
    })
    msg.success('高级配置已重置')
    emit('reset')
  } catch (e) {
    msg.error('重置高级配置失败')
  }
}

async function loadOutcrops(force = false) {
  if (loaded.value.report && !force) return
  loading.value.report = true
  try {
    const files = (await api.scan_files(force)) as any[]
    outcropOptions.value = files
      .filter((f: any) => f.status === 'completed')
      .map((f: any) => f.outcrop)
    loaded.value.report = true
  } catch (e) {
    console.error('[DevPanel] 加载露头选项失败', e)
    msg.error('加载露头选项失败')
  } finally {
    loading.value.report = false
  }
}

const reportFilters: Record<string, string> = {
  docx: 'Word 文档 (*.docx)',
  pdf: 'PDF 文件 (*.pdf)',
  both: 'ZIP 压缩包 (*.zip)',
}

async function generateReport() {
  let targets: string[] = []
  if (reportScope.value === 'selected') {
    if (selectedOutcrops.value.length === 0) {
      msg.warning('请至少选择一个露头')
      return
    }
    targets = selectedOutcrops.value
  } else {
    targets = outcropOptions.value
    if (targets.length === 0) {
      msg.warning('没有已完成的露头可导出')
      return
    }
  }

  const fmt = reportFmt.value
  const isSingleDirect = targets.length === 1 && fmt !== 'both'

  // 单文件且格式为 docx/pdf 时直接下载；否则打包为 ZIP
  let defaultName: string
  let filter: string
  if (isSingleDirect) {
    const ext = fmt === 'docx' ? 'docx' : 'pdf'
    defaultName = `report_${targets[0]}.${ext}`
    filter = reportFilters[fmt]
  } else {
    defaultName = targets.length === 1
      ? `report_${targets[0]}.zip`
      : `reports_${new Date().toISOString().slice(0, 10)}.zip`
    filter = reportFilters.both
  }

  const savePath = await api.ask_save_path(defaultName, filter)
  if (!savePath) {
    // 用户取消选择
    return
  }

  reportLoading.value = true
  reportProgressVisible.value = true
  reportProgress.value = { type: 'progress', message: '正在准备导出...' }
  startReportProgressPolling()
  try {
    if (isSingleDirect) {
      const res = (await api.generate_report(targets[0], reportType.value, fmt, savePath)) as Record<string, unknown>
      if (res.status === 'busy') {
        msg.warning((res.message as string) || '已有报告任务正在运行')
      } else if (res.error) {
        msg.error(res.error as string)
      } else if (res.docx_error || res.pdf_error) {
        msg.error(`生成失败: ${(res.docx_error as string) || ''} ${(res.pdf_error as string) || ''}`.trim())
      } else if (res.path) {
        msg.success(`报告已保存: ${res.path as string}`)
      } else {
        msg.warning('未能生成报告，请检查日志')
        console.warn('[DevPanel] generate_report 返回异常:', res)
      }
    } else {
      const res = (await api.generate_reports_zip(targets, reportType.value, fmt, savePath)) as Record<string, unknown>
      if (res.status === 'busy') {
        msg.warning((res.message as string) || '已有报告任务正在运行')
      } else if (res.error) {
        msg.error(res.error as string)
      } else if (res.zip_path) {
        msg.success(`报告已保存: ${res.zip_path as string}`)
      } else {
        msg.warning('未能生成报告压缩包，请检查日志')
        console.warn('[DevPanel] generate_reports_zip 返回异常:', res)
      }
    }
  } catch (e) {
    console.error('[DevPanel] 导出报告异常:', e)
    msg.error('导出报告失败')
  } finally {
    reportLoading.value = false
    // 停止轮询（但已完成事件已在 startReportProgressPolling 中处理完成，2s 后隐藏）
  }
}

async function loadAudit() {
  loading.value.audit = true
  try {
    auditLogs.value = (await api.get_audit_log(50)) as any[]
    loaded.value.audit = true
  } catch (e) {
    console.error('[DevPanel] 加载审计日志失败', e)
    msg.error('加载审计日志失败')
  } finally {
    loading.value.audit = false
  }
}

// 监听折叠面板展开，实现懒加载
function onCollapseChange(active: string | string[]) {
  const names = Array.isArray(active) ? active : [active]
  if (names.includes('report')) {
    // 若缓存已失效（如处理完成后），强制重新加载
    loadOutcrops(!cacheStore.isScanValid)
  }
  if (names.includes('backend-log') && !loaded.value.backendLog) {
    loadBackendLogs()
  }
}

// KeepAlive 激活时，若扫描缓存已失效则自动刷新报告露头列表
onActivated(() => {
  if (!cacheStore.isScanValid) {
    loadOutcrops(true)
  }
})
</script>

<style scoped lang="scss">
.dev-panel {
  background: var(--tp-surface-cyber);
  border-radius: var(--tp-radius-lg);
  padding: var(--tp-space-4) var(--tp-space-5);
  box-shadow: var(--tp-shadow-md), inset 0 1px 0 rgba(255,255,255,0.72);
  border: 1px solid rgba(125, 211, 252, 0.18);
  margin-top: var(--tp-space-4);
}
:deep(.el-collapse) {
  border-top: none;
  border-bottom: none;
}
:deep(.el-collapse-item__header) {
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  height: 44px;
  line-height: 44px;
}
:deep(.el-collapse-item__content) {
  padding-bottom: var(--tp-space-1);
}
.outcrop-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--tp-space-2);
}
.oc-tag {
  font-family: var(--tp-font-data);
}
.oc-empty {
  color: var(--tp-text-muted);
  font-size: 13px;
}
.log-controls {
  display: flex;
  gap: var(--tp-space-2);
  margin-bottom: var(--tp-space-3);
  align-items: center;
}
.backend-log-content {
  background:
    linear-gradient(rgba(2, 132, 199, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(2, 132, 199, 0.03) 1px, transparent 1px),
    var(--tp-bg-sunken);
  background-size: 24px 24px;
  border: 1px solid var(--tp-border-light);
  border-radius: var(--tp-radius-sm);
  padding: var(--tp-space-3);
  max-height: 350px;
  overflow: auto;
}
.backend-log-content pre {
  margin: 0;
  font-family: var(--tp-font-mono);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--tp-text-primary);
}
.dev-action-bar {
  display: flex;
  gap: var(--tp-space-3);
  margin-top: var(--tp-space-4);
  padding-top: var(--tp-space-3);
  border-top: 1px solid var(--tp-border-light);
  justify-content: flex-end;
}
.audit-scroll-container {
  max-height: 300px;
  overflow-y: auto;
}
.audit-list {
  display: flex;
  flex-direction: column;
  gap: var(--tp-space-2);
}
.audit-item {
  display: flex;
  gap: var(--tp-space-3);
  padding: var(--tp-space-2) var(--tp-space-3);
  border-radius: var(--tp-radius-xs);
  background: rgba(238, 240, 244, 0.74);
  border: 1px solid var(--tp-border-light);
  font-size: 13px;
  line-height: 1.6;
}
.audit-item:hover {
  border-color: rgba(56, 189, 248, 0.20);
  box-shadow: var(--tp-glow-cyan-sm);
}
.audit-time {
  color: var(--tp-text-muted);
  font-family: var(--tp-font-mono);
  white-space: nowrap;
  flex-shrink: 0;
}
.audit-action {
  color: var(--tp-text-secondary);
}

/* 报告导出紧凑布局 */
.report-form .el-form-item {
  margin-bottom: var(--tp-space-3);
}
.report-form .el-row {
  align-items: center;
}
.report-action {
  margin-top: var(--tp-space-1);
  margin-bottom: 0 !important;
}

/* 报告导出进度条 */
.report-progress-area {
  margin-top: var(--tp-space-3);
  padding: var(--tp-space-3);
  border-radius: var(--tp-radius-sm);
  background: rgba(238, 240, 244, 0.74);
  border: 1px solid var(--tp-border-light);
}
.report-progress-message {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: var(--tp-space-2);
  font-size: 13px;
  color: var(--tp-text-secondary);
  min-height: 22px;
}
.report-progress-batch {
  font-family: var(--tp-font-data);
  color: var(--tp-text-tertiary);
  margin-left: 4px;
}
.tp-success-text {
  color: var(--tp-success);
  font-weight: 500;
}
.tp-error-text {
  color: var(--tp-error);
  font-weight: 500;
}
:deep(.report-progress-area .el-progress-bar__outer) {
  border-radius: var(--tp-radius-full);
  background: rgba(26, 54, 93, 0.10);
  box-shadow: inset 0 1px 4px rgba(26, 54, 93, 0.14);
  overflow: hidden;
}
:deep(.report-progress-area .el-progress-bar__inner) {
  border-radius: var(--tp-radius-full);
  transition: width 0.4s var(--tp-easing-expo);
}

/* 高级配置紧凑网格 */
.advanced-form .el-form-item {
  margin-bottom: var(--tp-space-2);
}
.adv-section {
  margin-bottom: var(--tp-space-3);
}
.adv-section:last-child {
  margin-bottom: 0;
}
.adv-section-title {
  position: relative;
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: var(--tp-space-4) 0 var(--tp-space-3);
  padding-bottom: var(--tp-space-2);
  padding-left: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}
.adv-section:first-child .adv-section-title {
  margin-top: 0;
}
.adv-section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 2px;
  bottom: 10px;
  width: 3px;
  background: var(--tp-brand-accent);
  border-radius: 2px;
}
</style>
