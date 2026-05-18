<template>
  <div class="dev-panel">
    <el-collapse v-model="activeNames" @change="onCollapseChange">
      <el-collapse-item title="毕设报告导出" name="report">
        <div v-loading="loading.report" class="report-form">
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
        </div>
      </el-collapse-item>

      <el-collapse-item title="操作审计日志" name="audit">
        <div class="audit-scroll-container" v-loading="loading.audit">
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
        <div class="backend-log-content" v-loading="backendLogLoading">
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
import { ref, onMounted, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/pywebview'
import { useConfigStore } from '@/stores/config'
import { useCacheStore } from '@/stores/cache'

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
const outcropOptions = ref<string[]>([])
const selectedOutcrops = ref<string[]>([])
const auditLogs = ref<any[]>([])
const advanced = ref({
  window_strategy: 'auto',
  auto_density_threshold: 5.0,
  tangent_window_count: 3,
  min_intersections: 5,
  node_merge_tolerance: 1e-6,
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
    console.error(e)
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
    advanced.value.node_merge_tolerance = cfg.node_merge_tolerance ?? 1e-6
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
    ElMessage.success('高级配置已保存')
    emit('saved')
  } catch (e) {
    ElMessage.error('保存高级配置失败')
  }
}

async function resetDevConfig() {
  advanced.value = {
    window_strategy: 'auto',
    auto_density_threshold: 5.0,
    tangent_window_count: 3,
    min_intersections: 5,
    node_merge_tolerance: 1e-6,
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
    ElMessage.success('高级配置已重置')
    emit('reset')
  } catch (e) {
    ElMessage.error('重置高级配置失败')
  }
}

async function loadOutcrops(force = false) {
  if (loaded.value.report && !force) return
  loading.value.report = true
  try {
    const files = await api.scan_files(force)
    outcropOptions.value = files
      .filter((f: any) => f.status === 'completed')
      .map((f: any) => f.outcrop)
    loaded.value.report = true
  } catch (e) {
    console.error(e)
  } finally {
    loading.value.report = false
  }
}

async function generateReport() {
  let targets: string[] = []
  if (reportScope.value === 'selected') {
    if (selectedOutcrops.value.length === 0) {
      ElMessage.warning('请至少选择一个露头')
      return
    }
    targets = selectedOutcrops.value
  } else {
    targets = outcropOptions.value
    if (targets.length === 0) {
      ElMessage.warning('没有已完成的露头可导出')
      return
    }
  }

  // 让用户选择保存位置
  const defaultName = targets.length === 1
    ? `report_${targets[0]}.zip`
    : `reports_${new Date().toISOString().slice(0, 10)}.zip`
  const savePath = await api.ask_save_path(defaultName, 'ZIP 文件 (*.zip)')
  if (!savePath) {
    // 用户取消选择
    return
  }

  reportLoading.value = true
  try {
    const res = await api.generate_reports_zip(targets, reportType.value, reportFmt.value, savePath)
    if (res.error) {
      ElMessage.error(res.error)
    } else if (res.zip_path) {
      ElMessage.success(`报告已保存: ${res.zip_path}`)
    }
  } catch (e) {
    ElMessage.error('打包报告失败')
  } finally {
    reportLoading.value = false
  }
}

async function loadAudit() {
  loading.value.audit = true
  try {
    auditLogs.value = await api.get_audit_log(50)
    loaded.value.audit = true
  } catch (e) {
    console.error(e)
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
  background: var(--tp-bg-card);
  border-radius: var(--tp-radius-lg);
  padding: var(--tp-space-4) var(--tp-space-5);
  box-shadow: var(--tp-shadow-md);
  border: 1px solid var(--tp-border-light);
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
  background: var(--tp-bg-sunken);
  border: 1px solid var(--tp-border-light);
  border-radius: var(--tp-radius-sm);
  padding: var(--tp-space-3);
  max-height: 350px;
  overflow: auto;
}
.backend-log-content pre {
  margin: 0;
  font-family: var(--tp-font-mono);
  font-size: 12px;
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
  background: var(--tp-bg-sunken);
  border: 1px solid var(--tp-border-light);
  font-size: 13px;
  line-height: 1.6;
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
