<template>
  <div class="comparison-view">
    <h2 class="page-title">对比</h2>

    <el-empty v-if="!loading && tableData.length === 0" description="暂无露头数据" />

    <div v-else class="table-card tp-card">
      <table class="native-table" v-if="!loading && tableData.length">
        <thead>
          <tr>
            <th>露头</th>
            <th>迹线数</th>
            <th>P10</th>
            <th>P20</th>
            <th>P21</th>
            <th>平均迹长(m)</th>
            <th>走向</th>
            <th>I:II:III</th>
            <th v-if="pipelineStore.lastEnableNodeRecognition">节点总数</th>
            <th v-if="pipelineStore.lastEnableNodeRecognition">X:Y:I</th>
            <th v-if="pipelineStore.lastEnableNodeRecognition">节点密度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in tableData" :key="row.outcrop">
            <td :title="row.outcrop">{{ row.outcrop }}</td>
            <td :title="row.trace_count">{{ row.trace_count }}</td>
            <td :title="row.p10">{{ row.p10 }}</td>
            <td :title="row.p20">{{ row.p20 }}</td>
            <td :title="row.p21">{{ row.p21 }}</td>
            <td :title="row.mean_trace_length">{{ row.mean_trace_length }}</td>
            <td :title="row.scanline_azimuth">{{ row.scanline_azimuth }}</td>
            <td :title="row.type_ratio">{{ row.type_ratio }}</td>
            <td v-if="pipelineStore.lastEnableNodeRecognition" :title="row.node_count">{{ row.node_count }}</td>
            <td v-if="pipelineStore.lastEnableNodeRecognition" :title="row.node_ratio">{{ row.node_ratio }}</td>
            <td v-if="pipelineStore.lastEnableNodeRecognition" :title="row.node_density">{{ row.node_density }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="loading" class="table-loading">加载中...</div>
    </div>

    <div class="chart-area tp-card" v-if="tableData.length > 0">
      <div class="chart-header">
        <div class="chart-header-left">
          <div class="chart-icon">
            <el-icon :size="16"><TrendCharts /></el-icon>
          </div>
          <h3>多露头参数对比</h3>
        </div>
        <div class="chart-tip">点击图例可控制显示/隐藏</div>
      </div>
      <div class="chart-toolbar">
        <el-radio-group v-model="chartMetric" size="small">
          <el-radio-button label="density">密度指标</el-radio-button>
          <el-radio-button label="type">裂隙类型</el-radio-button>
          <el-radio-button v-if="pipelineStore.lastEnableNodeRecognition" label="node">节点指标</el-radio-button>
          <el-radio-button label="length">面积/长度</el-radio-button>
        </el-radio-group>
      </div>
      <v-chart class="chart" :option="barOption" autoresize />
    </div>

    <!-- 所有露头图片网格展示区 -->
    <div class="images-panel tp-card" v-if="allImages.length > 0">
      <div class="images-panel-header">
        <div class="images-header-left">
          <div class="images-icon">
            <el-icon :size="16"><Picture /></el-icon>
          </div>
          <h3>处理结果图</h3>
        </div>
        <div class="image-filter-bar">
          <el-radio-group v-model="imageFilter" size="small">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="原始迹线">原始迹线</el-radio-button>
            <el-radio-button label="旋转迹线">旋转迹线</el-radio-button>
            <el-radio-button v-if="pipelineStore.lastExportRosePlot" label="走向玫瑰">走向玫瑰</el-radio-button>
          </el-radio-group>
          <el-input v-model="imageSearch" placeholder="搜索露头..." size="small" style="width:160px" clearable />
        </div>
      </div>
      <div class="image-grid">
        <div
          class="image-card"
          v-for="img in filteredImages"
          :key="img.outcrop + img.type"
          @click="openViewer(img)"
        >
          <div class="image-label">{{ img.outcrop }} · {{ img.type }}</div>
          <div class="image-wrapper">
            <img :src="img.src" class="grid-img" />
          </div>
        </div>
      </div>
    </div>
    <el-empty v-else-if="!loading && filteredImages.length === 0 && allImages.length > 0" description="无匹配图片" style="margin-top:16px" />
    <el-empty v-else-if="!loading" description="暂无图片" style="margin-top:16px" />

    <ImageViewer
      v-model:visible="viewerVisible"
      :images="viewerImages"
      :initial-index="viewerInitialIndex"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onActivated, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { TrendCharts, Picture } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import ImageViewer from '@/components/ImageViewer.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useCacheStore } from '@/stores/cache'
import { api } from '@/api/pywebview'
import { loadImageBase64 } from '@/utils/image'
import type { ComparisonRow, PipelineResult } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

defineOptions({ name: 'Comparison' })

const pipelineStore = usePipelineStore()
const cacheStore = useCacheStore()

const tableData = ref<ComparisonRow[]>([])
const loading = ref(false)
const chartMetric = ref('density')

// 图片筛选
const imageFilter = ref('all')
const imageSearch = ref('')

watch(() => pipelineStore.lastExportRosePlot, (val) => {
  if (!val && imageFilter.value === '走向玫瑰') {
    imageFilter.value = 'all'
  }
})

const filteredImages = computed(() => {
  let list = allImages.value
  if (imageFilter.value !== 'all') {
    list = list.filter(img => img.type === imageFilter.value)
  }
  if (imageSearch.value.trim()) {
    const kw = imageSearch.value.trim().toLowerCase()
    list = list.filter(img => img.outcrop.toLowerCase().includes(kw))
  }
  return list
})

// 图片网格 — 所有露头的所有图片
interface GridImage {
  outcrop: string
  type: string
  src: string
}
const allImages = ref<GridImage[]>([])

const viewerVisible = ref(false)
const viewerImages = ref<Array<{ title: string; src: string }>>([])
const viewerInitialIndex = ref(0)

function openViewer(img: GridImage) {
  viewerImages.value = allImages.value.map(item => ({
    title: `${item.outcrop} · ${item.type}`,
    src: item.src,
  }))
  // 在全部图片中找到当前图片的索引
  const allIndex = allImages.value.findIndex(
    item => item.outcrop === img.outcrop && item.type === img.type
  )
  viewerInitialIndex.value = Math.max(0, allIndex)
  viewerVisible.value = true
}

function safeFloat(val: string): number | null {
  if (val === '—' || val == null || val === '') return null
  const n = parseFloat(val)
  return isNaN(n) ? null : n
}

const echartsFont = 'var(--tp-font-data)'

const GEO_C1 = '#C96B4F'
const GEO_C2 = '#4A7C9B'
const GEO_C3 = '#4A9E7A'
const GEO_C4 = '#6B8EBB'
const GEO_C5 = '#8AAFC4'

const barOption = computed(() => {
  const outcrops = tableData.value.map(d => d.outcrop)
  const metric = chartMetric.value

  const base = {
    title: { text: '多露头参数对比', left: 'center', textStyle: { fontFamily: echartsFont, fontSize: 14, fontWeight: 600, color: 'var(--tp-text-primary)' } },
    tooltip: { trigger: 'axis', textStyle: { fontFamily: echartsFont } },
    legend: { bottom: 0, textStyle: { fontFamily: echartsFont, color: 'var(--tp-text-secondary)' } },
    grid: { left: '10%', right: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: outcrops, axisLabel: { fontFamily: echartsFont, color: 'var(--tp-text-secondary)' }, axisLine: { lineStyle: { color: 'var(--tp-border)' } } },
    yAxis: { type: 'value', axisLabel: { fontFamily: echartsFont, color: 'var(--tp-text-secondary)' }, splitLine: { lineStyle: { color: 'var(--tp-border-light)' } } },
  }

  if (metric === 'density') {
    return {
      ...base,
      legend: { data: ['P10', 'P20', 'P21'], bottom: 0, textStyle: { fontFamily: echartsFont, color: 'var(--tp-text-secondary)' } },
      series: [
        { name: 'P10', type: 'bar', data: tableData.value.map(d => safeFloat(d.p10) ?? '-'), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] } },
        { name: 'P20', type: 'bar', data: tableData.value.map(d => safeFloat(d.p20) ?? '-'), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] } },
        { name: 'P21', type: 'bar', data: tableData.value.map(d => safeFloat(d.p21) ?? '-'), itemStyle: { color: GEO_C3, borderRadius: [3, 3, 0, 0] } },
      ],
    }
  }

  if (metric === 'type') {
    return {
      ...base,
      legend: { data: ['I型', 'II型', 'III型', '总裂隙数'], bottom: 0, textStyle: { fontFamily: echartsFont, color: 'var(--tp-text-secondary)' } },
      series: [
        { name: 'I型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[0]) ?? 0), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] } },
        { name: 'II型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[1]) ?? 0), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] } },
        { name: 'III型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[2]) ?? 0), itemStyle: { color: GEO_C3, borderRadius: [3, 3, 0, 0] } },
        { name: '总裂隙数', type: 'bar', data: tableData.value.map(d => {
          const parts = d.type_ratio.split(':')
          const sum = (safeFloat(parts[0]) ?? 0) + (safeFloat(parts[1]) ?? 0) + (safeFloat(parts[2]) ?? 0)
          return sum
        }), itemStyle: { color: GEO_C4, borderRadius: [3, 3, 0, 0] } },
      ],
    }
  }

  if (metric === 'node') {
    return {
      ...base,
      legend: { data: ['节点总数', 'X节点', 'Y节点', 'I节点'], bottom: 0, textStyle: { fontFamily: echartsFont, color: 'var(--tp-text-secondary)' } },
      series: [
        { name: '节点总数', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_count) ?? '-'), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] } },
        { name: 'X节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[0]) ?? 0), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] } },
        { name: 'Y节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[1]) ?? 0), itemStyle: { color: GEO_C3, borderRadius: [3, 3, 0, 0] } },
        { name: 'I节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[2]) ?? 0), itemStyle: { color: GEO_C5, borderRadius: [3, 3, 0, 0] } },
      ],
    }
  }

  // metric === 'length'
  const series: any[] = [
    { name: '平均迹长', type: 'bar', data: tableData.value.map(d => safeFloat(d.mean_trace_length) ?? '-'), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] } },
  ]
  if (pipelineStore.lastEnableNodeRecognition) {
    series.push({ name: '节点密度', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_density) ?? '-'), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] } })
  }
  return {
    ...base,
    legend: { data: series.map(s => s.name), bottom: 0, textStyle: { fontFamily: echartsFont, color: 'var(--tp-text-secondary)' } },
    series,
  }
})

let isLoadingComparison = false
let hasInitializedComparison = false

async function loadComparison(force = false) {
  if (isLoadingComparison) {
    console.warn('[ComparisonView] loadComparison 被重复调用，已忽略')
    return
  }
  isLoadingComparison = true
  loading.value = true
  try {
    let files = force ? null : cacheStore.getScan()
    if (!files) {
      files = await api.scan_files(force)
      cacheStore.setScan(files!)
    }
    const outcrops = files!.map((f: any) => f.outcrop)
    if (outcrops.length === 0) {
      tableData.value = []
      allImages.value = []
      return
    }

    let data = force ? null : cacheStore.getComparison()
    if (!data) {
      data = await api.get_comparison(outcrops)
      cacheStore.setComparison(data!)
    }
    tableData.value = data!.map((d: any) => {
      const ns = d.nodes_summary || {}
      const nodeCount = ns.node_count ?? 0
      const outcropArea = d.outcrop_area ?? 0
      const nodeDensity = (outcropArea > 0) ? (nodeCount / outcropArea).toFixed(4) : '—'
      return {
        outcrop: d.outcrop,
        trace_count: (d.trace_count ?? '—') + '',
        p10: d.p10 != null ? Number(d.p10).toFixed(2) : '—',
        p20: d.p20 != null ? Number(d.p20).toFixed(2) : '—',
        p21: d.p21 != null ? Number(d.p21).toFixed(2) : '—',
        mean_trace_length: d.mean_trace_length != null ? Number(d.mean_trace_length).toFixed(2) : '—',
        scanline_azimuth: (d.scanline_azimuth ?? '—') + '°',
        type_ratio: `${d.type_i ?? 0}:${d.type_ii ?? 0}:${d.type_iii ?? 0}`,
        node_count: (ns.node_count ?? '—') + '',
        node_ratio: `${ns.node_x_count ?? 0}:${ns.node_y_count ?? 0}:${ns.node_i_count ?? 0}`,
        node_density: nodeDensity,
      }
    })

    // 加载所有露头的所有图片（结果列表走缓存）
    let results = force ? null : cacheStore.getResults()
    if (!results) {
      results = await api.get_results()
      cacheStore.setResults(results!)
    }
    const images: GridImage[] = []
    for (const result of results!) {
      if (result.raw_plot) {
        images.push({
          outcrop: result.outcrop,
          type: '原始迹线',
          src: await loadImageBase64(result.raw_plot),
        })
      }
      if (result.rotated_plot) {
        images.push({
          outcrop: result.outcrop,
          type: '旋转迹线',
          src: await loadImageBase64(result.rotated_plot),
        })
      }
      if (pipelineStore.lastExportRosePlot && result.rose_plot) {
        images.push({
          outcrop: result.outcrop,
          type: '走向玫瑰',
          src: await loadImageBase64(result.rose_plot),
        })
      }
    }
    allImages.value = images
  } catch (e) {
    console.error('对比页加载失败', e)
    ElMessage.error('对比页加载失败')
  } finally {
    loading.value = false
    isLoadingComparison = false
  }
}

onMounted(() => {
  hasInitializedComparison = true
  loadComparison()
})

onActivated(() => {
  if (!hasInitializedComparison) {
    hasInitializedComparison = true
    loadComparison()
  } else if (!cacheStore.isComparisonValid || !cacheStore.isScanValid || !cacheStore.isResultsValid) {
    cacheStore.invalidateComparison()
    cacheStore.invalidateResults()
    loadComparison(true)
  }
})
</script>

<style scoped lang="scss">
.comparison-view {
  padding: var(--tp-space-5) var(--tp-space-6);
  flex-shrink: 0;
}

.page-title {
  font-family: var(--tp-font-heading);
  font-size: 22px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin-bottom: var(--tp-space-4);
}

/* ── 表格卡片 ── */
.table-card {
  padding: var(--tp-space-4);
  margin-bottom: var(--tp-space-4);
}

.table-card:hover {
  transform: none;
  box-shadow: var(--tp-shadow-md);
}

/* ── 原生表格样式（替代 el-table）── */
.native-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--tp-font-body);
  font-size: 12px;
  color: var(--tp-text-primary);
  border: 1px solid var(--tp-border-light);
  table-layout: fixed;
}

.native-table thead {
  background: var(--tp-bg-sunken);
}

.native-table th {
  font-family: var(--tp-font-heading);
  font-weight: 600;
  color: var(--tp-text-primary);
  padding: 6px 8px;
  text-align: left;
  border-bottom: 1px solid var(--tp-border-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.native-table td {
  padding: 5px 8px;
  border-bottom: 1px solid var(--tp-border-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.native-table tbody tr:hover {
  background: var(--tp-bg-hover);
}

.native-table tbody tr:last-child td {
  border-bottom: none;
}

/* 列宽分配 */
.native-table th:nth-child(1), .native-table td:nth-child(1) { width: 7%; }   /* 露头 */
.native-table th:nth-child(2), .native-table td:nth-child(2) { width: 8%; }   /* 迹线数 */
.native-table th:nth-child(3), .native-table td:nth-child(3) { width: 8%; }   /* P10 */
.native-table th:nth-child(4), .native-table td:nth-child(4) { width: 8%; }   /* P20 */
.native-table th:nth-child(5), .native-table td:nth-child(5) { width: 8%; }   /* P21 */
.native-table th:nth-child(6), .native-table td:nth-child(6) { width: 11%; }  /* 平均迹长 */
.native-table th:nth-child(7), .native-table td:nth-child(7) { width: 7%; }   /* 走向 */
.native-table th:nth-child(8), .native-table td:nth-child(8) { width: 10%; }  /* I:II:III */
.native-table th:nth-child(9), .native-table td:nth-child(9) { width: 9%; }   /* 节点总数 */
.native-table th:nth-child(10), .native-table td:nth-child(10) { width: 9%; }  /* X:Y:I */
.native-table th:nth-child(11), .native-table td:nth-child(11) { width: 10%; } /* 节点密度 */

.table-loading {
  padding: 40px 0;
  text-align: center;
  color: var(--tp-text-muted);
  font-size: 14px;
}

/* ── 图表区 ── */
.chart-area {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-top: var(--tp-space-4);
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
  flex-wrap: wrap;
  gap: var(--tp-space-2);
}

.chart-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chart-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--tp-radius-sm);
  background: var(--tp-info-bg);
  color: var(--tp-info);
}

.chart-area h3 {
  font-family: var(--tp-font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0;
}

.chart-toolbar {
  display: flex;
  justify-content: center;
  margin-bottom: var(--tp-space-3);
}

.chart-tip {
  font-size: 13px;
  color: var(--tp-text-muted);
}

.chart {
  height: 300px;
}

/* ── 图片网格 ── */
.images-panel {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-top: var(--tp-space-4);
}

.images-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--tp-space-3);
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}

.images-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.images-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-brand-accent-bg);
  color: var(--tp-brand-accent);
}

.images-panel-header h3 {
  font-family: var(--tp-font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0;
}

.image-filter-bar {
  display: flex;
  align-items: center;
  gap: var(--tp-space-3);
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--tp-space-3);
}

.image-card {
  background: var(--tp-bg-sunken);
  border-radius: var(--tp-radius-md);
  overflow: hidden;
  cursor: zoom-in;
  transition: all var(--tp-duration-slow) var(--tp-easing-expo);
  border: 1px solid var(--tp-border-light);
}

.image-card:hover {
  box-shadow: var(--tp-shadow-md), 0 0 0 1px var(--tp-brand-accent-border);
  transform: translateY(-3px) scale(1.02);
  border-color: var(--tp-border-medium);
}

.image-label {
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--tp-text-primary);
  background: var(--tp-bg-hover);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--tp-font-heading);
  border-bottom: 1px solid var(--tp-border-light);
}

.image-wrapper {
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
}

.grid-img {
  max-width: 100%;
  max-height: 160px;
  object-fit: contain;
}
</style>
