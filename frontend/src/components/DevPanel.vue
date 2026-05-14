<template>
  <div class="dev-panel">
    <el-collapse v-model="activeNames">
      <el-collapse-item title="📊 毕设报告导出" name="report">
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
      </el-collapse-item>

      <el-collapse-item title="📋 数据溯源面板" name="provenance">
        <el-descriptions v-if="provenance" :column="1" border size="small">
          <el-descriptions-item label="露头">{{ provenance.outcrop }}</el-descriptions-item>
          <el-descriptions-item label="P10">{{ provenance.p10?.value }} [{{ provenance.p10?.source }}]</el-descriptions-item>
          <el-descriptions-item label="P20">{{ provenance.p20?.value }} [{{ provenance.p20?.source }}]</el-descriptions-item>
          <el-descriptions-item label="P21">{{ provenance.p21?.value }} [{{ provenance.p21?.source }}]</el-descriptions-item>
          <el-descriptions-item label="面积来源">{{ provenance.area_source }}</el-descriptions-item>
          <el-descriptions-item v-if="provenance.warning" label="警告">
            <span style="color:#c0392b">{{ provenance.warning }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="选择露头后查看溯源" />
      </el-collapse-item>

      <el-collapse-item title="🔍 操作审计日志" name="audit">
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
      </el-collapse-item>

      <el-collapse-item title="⚙️ 高级配置" name="advanced">
        <el-form label-width="140px" size="small">
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
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/pywebview'
import { loadImageBase64 } from '@/utils/image'

const props = defineProps<{
  outcrop: string
}>()

const activeNames = ref(['report'])
const reportScope = ref('selected')
const reportType = ref('full')
const reportFmt = ref('docx')
const reportLoading = ref(false)
const outcropOptions = ref<string[]>([])
const selectedOutcrops = ref<string[]>([])
const provenance = ref<any>(null)
const auditLogs = ref<any[]>([])
const advanced = ref({
  split_ratios: '0.25, 0.5, 0.75',
  radius_ratios: '1.0, 0.75, 0.5',
  min_intersections: 5,
  hull_buffer_ratio: 0.25,
  disagreement_threshold: '',
})

async function loadOutcrops() {
  try {
    const files = await api.scan_files()
    outcropOptions.value = files
      .filter((f: any) => f.status === 'completed')
      .map((f: any) => f.outcrop)
  } catch (e) {
    console.error(e)
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
  provenance.value = await api.get_provenance(props.outcrop)
}

async function loadAudit() {
  auditLogs.value = await api.get_audit_log(50)
}

watch(() => props.outcrop, () => {
  loadProvenance()
})

onMounted(() => {
  loadAudit()
  loadProvenance()
  loadOutcrops()
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
</style>
