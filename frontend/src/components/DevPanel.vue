<template>
  <div class="dev-panel">
    <el-collapse v-model="activeNames" @change="onCollapseChange">
      <el-collapse-item title="毕设报告导出" name="report">
        <div v-loading="loading.report">
          <el-form label-width="100px" size="small">
            <el-form-item label="导出范围">
              <el-radio-group v-model="reportScope">
                <el-radio-button label="selected">指定露头</el-radio-button>
                <el-radio-button label="all">全部已处理</el-radio-button>
              </el-radio-group>
            </el-form-item>
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
            <el-form-item label="报告类型">
              <el-radio-group v-model="reportType">
                <el-radio-button label="full">完整报告</el-radio-button>
                <el-radio-button label="stats">仅统计</el-radio-button>
                <el-radio-button label="plots">仅图表</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="格式">
              <el-radio-group v-model="reportFmt">
                <el-radio-button label="docx">Word</el-radio-button>
                <el-radio-button label="pdf">PDF</el-radio-button>
                <el-radio-button label="both">两者</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="reportLoading" @click="generateReport">
                生成并导出报告
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-collapse-item>

      <el-collapse-item title="数据溯源面板" name="provenance">
        <div v-loading="loading.provenance">
          <el-descriptions v-if="provenance" :column="1" border size="small">
            <el-descriptions-item label="露头">{{ provenance.outcrop }}</el-descriptions-item>
            <el-descriptions-item label="P10">{{ provenance.p10?.value }} [{{ provenance.p10?.source }}]</el-descriptions-item>
            <el-descriptions-item label="P20">{{ provenance.p20?.value }} [{{ provenance.p20?.source }}]</el-descriptions-item>
            <el-descriptions-item label="P21">{{ provenance.p21?.value }} [{{ provenance.p21?.source }}]</el-descriptions-item>
            <el-descriptions-item label="面积来源">{{ formatAreaSource(provenance.area_source) }}</el-descriptions-item>
            <el-descriptions-item v-if="provenance.warning" label="警告">
              <span style="color:#c0392b">{{ provenance.warning }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="选择露头后查看溯源" />
        </div>
      </el-collapse-item>

      <el-collapse-item title="操作审计日志" name="audit">
        <div v-loading="loading.audit">
          <el-timeline>
            <el-timeline-item
              v-for="item in auditLogs"
              :key="item.timestamp"
              :timestamp="item.timestamp"
            >
              {{ item.action }} — {{ item.result }}
            </el-timeline-item>
          </el-timeline>
          <el-button size="small" @click="loadAudit">刷新</el-button>
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
        <el-form label-width="140px" size="small">
          <el-form-item label="切圆数量">
            <el-input-number v-model="advanced.tangent_window_count" :min="1" :max="20" :step="1" />
          </el-form-item>
          <el-form-item label="显示节点覆盖层">
            <el-switch v-model="advanced.show_node_overlay" />
          </el-form-item>
          <el-form-item label="切分比例">
            <el-input v-model="advanced.split_ratios" />
          </el-form-item>
          <el-form-item label="半径比例">
            <el-input v-model="advanced.radius_ratios" />
          </el-form-item>
          <el-form-item label="最小交点数">
            <el-input-number v-model="advanced.min_intersections" :min="1" :max="20" />
          </el-form-item>
          <el-form-item label="凸包缓冲比">
            <el-input-number v-model="advanced.hull_buffer_ratio" :min="0" :max="1" :step="0.05" />
          </el-form-item>
          <el-form-item label="差异阈值">
            <el-input v-model="advanced.disagreement_threshold" placeholder="auto" />
          </el-form-item>
        </el-form>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/pywebview'
import { formatAreaSource } from '@/utils/format'
import { useConfigStore } from '@/stores/config'

const props = defineProps<{
  outcrop: string
}>()

const configStore = useConfigStore()

const activeNames = ref<string[]>([])
const reportScope = ref('selected')
const reportType = ref('full')
const reportFmt = ref('docx')
const reportLoading = ref(false)
const outcropOptions = ref<string[]>([])
const selectedOutcrops = ref<string[]>([])
const provenance = ref<any>(null)
const auditLogs = ref<any[]>([])
const advanced = ref({
  tangent_window_count: 3,
  show_node_overlay: true,
  split_ratios: '0.25, 0.5, 0.75',
  radius_ratios: '1.0, 0.75, 0.5',
  min_intersections: 5,
  hull_buffer_ratio: 0.25,
  disagreement_threshold: '',
})

// 各面板的加载状态
const loading = ref({
  report: false,
  provenance: false,
  audit: false,
  backendLog: false,
})

// 各面板是否已加载过（避免重复加载）
const loaded = ref({
  report: false,
  provenance: false,
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
  // 从全局配置初始化高级配置字段
  try {
    const cfg = await configStore.loadConfig()
    advanced.value.tangent_window_count = cfg.tangent_window_count ?? 3
    advanced.value.show_node_overlay = cfg.show_node_overlay ?? true
  } catch (e) {
    // ignore
  }
})

// 监听高级配置变化，自动保存到全局配置
watch(
  () => [advanced.value.tangent_window_count, advanced.value.show_node_overlay],
  async () => {
    try {
      await configStore.saveConfig({
        tangent_window_count: advanced.value.tangent_window_count,
        show_node_overlay: advanced.value.show_node_overlay,
      })
    } catch (e) {
      // ignore save errors
    }
  },
  { deep: true }
)

async function loadOutcrops() {
  if (loaded.value.report) return
  loading.value.report = true
  try {
    const files = await api.scan_files()
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

  reportLoading.value = true
  try {
    const res = await api.generate_reports_zip(targets, reportType.value, reportFmt.value)
    if (res.error) {
      ElMessage.error(res.error)
    } else if (res.zip_path) {
      ElMessage.success(`批量报告已打包: ${res.zip_path}`)
    }
  } catch (e) {
    ElMessage.error('打包报告失败')
  } finally {
    reportLoading.value = false
  }
}

async function loadProvenance() {
  if (!props.outcrop) return
  if (loaded.value.provenance && provenance.value?.outcrop === props.outcrop) return
  loading.value.provenance = true
  try {
    provenance.value = await api.get_provenance(props.outcrop)
    loaded.value.provenance = true
  } catch (e) {
    console.error(e)
  } finally {
    loading.value.provenance = false
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
  if (names.includes('report') && !loaded.value.report) {
    loadOutcrops()
  }
  if (names.includes('provenance') && (!loaded.value.provenance || provenance.value?.outcrop !== props.outcrop)) {
    loadProvenance()
  }
  if (names.includes('audit') && !loaded.value.audit) {
    loadAudit()
  }
  if (names.includes('backend-log') && !loaded.value.backendLog) {
    loadBackendLogs()
  }
}

// 监听 outcrop 变化，如果溯源面板已展开则自动刷新
watch(() => props.outcrop, () => {
  loaded.value.provenance = false
  if (activeNames.value.includes('provenance')) {
    loadProvenance()
  }
})
</script>

<style scoped lang="scss">
.dev-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-top: 16px;
}
.outcrop-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.oc-tag {
  font-family: "Times New Roman", serif;
}
.oc-empty {
  color: #909399;
  font-size: 13px;
}
.log-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  align-items: center;
}
.backend-log-content {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  max-height: 350px;
  overflow: auto;
}
.backend-log-content pre {
  margin: 0;
  font-size: 12px;
  font-family: 'Consolas', 'Courier New', monospace;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  color: #2c3e50;
}
</style>
