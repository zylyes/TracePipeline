<template>
  <div class="comparison-view">
    <h2 class="page-title">对比</h2>

    <el-empty v-if="!loading && tableData.length === 0" description="暂无露头数据" />

    <div v-else class="table-card tp-card tp-neon-edge">
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
      <div v-if="loading" class="table-loading">
        <span class="tp-loading-orbit"></span>
        <div class="loading-copy">
          <span>正在汇总多露头参数</span>
          <span class="tp-skeleton-line"></span>
          <span class="tp-skeleton-line short"></span>
        </div>
      </div>
    </div>

    <div class="chart-area tp-card tp-neon-edge" v-if="tableData.length > 0">
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
      <v-chart class="chart" :option="barOption" :init-options="chartInitOpts" autoresize />
    </div>

    <!-- 所有露头图片网格展示区 -->
    <div class="images-panel tp-card tp-neon-edge" v-if="allImages.length > 0">
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
          @mouseenter="ensureThumbnailLoaded(img)"
          @click="openViewer(img)"
        >
          <div class="image-label">{{ img.outcrop }} · {{ img.type }}</div>
          <div class="image-wrapper">
            <img v-if="img.src" :src="img.src" class="grid-img" loading="lazy" />
            <div v-else class="image-placeholder" :class="{ loading: img.loading }">
              <span v-if="img.loading" class="tp-loading-orbit"></span>
              <span>{{ img.loading ? '缩略图生成中' : '悬停加载预览' }}</span>
            </div>
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
      @index-change="handleViewerIndexChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onActivated, computed } from 'vue'
import { msg } from '@/utils/message'
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
import { loadImageBase64, loadImageThumbnail } from '@/utils/image'
import { getChartColors, getEchartsFontFamily, getEchartsHeadingFont, cssVar, baseAnimationConfig, baseSeriesAnimation } from '@/utils/echarts-theme'
import type { ComparisonRow, PipelineResult } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

defineOptions({ name: 'Comparison' })

const pipelineStore = usePipelineStore()
const cacheStore = useCacheStore()
const INITIAL_IMAGE_PREFETCH_COUNT = 4
const IMAGE_PREFETCH_CONCURRENCY = 2
const GRID_THUMBNAIL_MAX_PX = 480
let activeImageLoads = 0
const imageLoadQueue: Array<() => void> = []

const tableData = ref<ComparisonRow[]>([])
const loading = ref(false)
const chartMetric = ref('density')
const chartInitOpts = { devicePixelRatio: Math.max(window.devicePixelRatio || 1, 2) }

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
  path: string
  src: string
  fullSrc?: string
  loading?: boolean
  thumbnailLoadPromise?: Promise<void>
  fullLoadPromise?: Promise<void>
}
const allImages = ref<GridImage[]>([])

const viewerVisible = ref(false)
const viewerImages = ref<Array<{ title: string; src: string }>>([])
const viewerInitialIndex = ref(0)

function syncViewerImages() {
  viewerImages.value = allImages.value.map(item => ({
    title: `${item.outcrop} · ${item.type}`,
    src: item.fullSrc || item.src,
  }))
}

function acquireImageLoadSlot(): Promise<() => void> {
  if (activeImageLoads < IMAGE_PREFETCH_CONCURRENCY) {
    activeImageLoads += 1
    return Promise.resolve(releaseImageLoadSlot)
  }
  return new Promise(resolve => {
    imageLoadQueue.push(() => {
      activeImageLoads += 1
      resolve(releaseImageLoadSlot)
    })
  })
}

function releaseImageLoadSlot() {
  activeImageLoads = Math.max(0, activeImageLoads - 1)
  const next = imageLoadQueue.shift()
  if (next) next()
}

async function ensureThumbnailLoaded(img: GridImage) {
  if (img.src || !img.path) return
  if (img.thumbnailLoadPromise) return img.thumbnailLoadPromise
  img.loading = true
  img.thumbnailLoadPromise = (async () => {
    const release = await acquireImageLoadSlot()
    try {
      if (!img.src) {
        img.src = await loadImageThumbnail(img.path, GRID_THUMBNAIL_MAX_PX)
        if (viewerVisible.value) syncViewerImages()
      }
    } finally {
      release()
      img.loading = false
      img.thumbnailLoadPromise = undefined
    }
  })()
  return img.thumbnailLoadPromise
}

async function ensureFullImageLoaded(img: GridImage) {
  if (img.fullSrc || !img.path) return
  if (img.fullLoadPromise) return img.fullLoadPromise
  img.fullLoadPromise = (async () => {
    const release = await acquireImageLoadSlot()
    try {
      if (!img.fullSrc) {
        img.fullSrc = await loadImageBase64(img.path)
        if (!img.src) img.src = img.fullSrc
        if (viewerVisible.value) syncViewerImages()
      }
    } finally {
      release()
      img.fullLoadPromise = undefined
    }
  })()
  return img.fullLoadPromise
}

function prefetchGridImages() {
  for (const img of filteredImages.value.slice(0, INITIAL_IMAGE_PREFETCH_COUNT)) {
    void ensureThumbnailLoaded(img)
  }
}

function prefetchNearbyImages(index: number) {
  for (const i of [index - 1, index, index + 1]) {
    const img = allImages.value[i]
    if (img) void ensureThumbnailLoaded(img)
  }
}

async function openViewer(img: GridImage) {
  await ensureThumbnailLoaded(img)
  await ensureFullImageLoaded(img)
  // 在全部图片中找到当前图片的索引
  const allIndex = allImages.value.findIndex(
    item => item.outcrop === img.outcrop && item.type === img.type
  )
  viewerInitialIndex.value = Math.max(0, allIndex)
  syncViewerImages()
  viewerVisible.value = true
  prefetchNearbyImages(viewerInitialIndex.value)
}

async function handleViewerIndexChange(index: number) {
  const img = allImages.value[index]
  if (img) await ensureFullImageLoaded(img)
}

watch(filteredImages, () => {
  prefetchGridImages()
})

function safeFloat(val: string): number | null {
  if (val === '—' || val == null || val === '') return null
  const n = parseFloat(val)
  return isNaN(n) ? null : n
}

const echartsFont = getEchartsFontFamily()
const echartsHeadingFont = getEchartsHeadingFont()

const chartColors = getChartColors()
const GEO_C1 = chartColors[0]
const GEO_C2 = chartColors[1]
const GEO_C3 = chartColors[2]
const GEO_C4 = chartColors[3]
const GEO_C5 = chartColors[5]

const barOption = computed(() => {
  const outcrops = tableData.value.map(d => d.outcrop)
  const metric = chartMetric.value

  const colorPrimary = cssVar('--tp-text-primary')
  const colorSecondary = cssVar('--tp-text-secondary')
  const colorBorder = cssVar('--tp-border')
  const colorBorderLight = cssVar('--tp-border-light')
  const legendTextStyle = { fontFamily: echartsFont, color: colorSecondary }

  const base = {
    ...baseAnimationConfig(),
    title: { text: '多露头参数对比', left: 'center', textStyle: { fontFamily: echartsHeadingFont, fontSize: 14, fontWeight: 600, color: colorPrimary } },
    tooltip: { trigger: 'axis', textStyle: { fontFamily: echartsFont } },
    legend: { bottom: 0, textStyle: legendTextStyle },
    grid: { left: '10%', right: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: outcrops, axisLabel: { fontFamily: echartsFont, color: colorSecondary }, axisLine: { lineStyle: { color: colorBorder } } },
    yAxis: { type: 'value', axisLabel: { fontFamily: echartsFont, color: colorSecondary }, splitLine: { lineStyle: { color: colorBorderLight } } },
  }

  if (metric === 'density') {
    return {
      ...base,
      legend: { data: ['P10', 'P20', 'P21'], bottom: 0, textStyle: legendTextStyle },
      series: [
        { name: 'P10', type: 'bar', data: tableData.value.map(d => safeFloat(d.p10) ?? '-'), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: 'P20', type: 'bar', data: tableData.value.map(d => safeFloat(d.p20) ?? '-'), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: 'P21', type: 'bar', data: tableData.value.map(d => safeFloat(d.p21) ?? '-'), itemStyle: { color: GEO_C3, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
      ],
    }
  }

  if (metric === 'type') {
    return {
      ...base,
      legend: { data: ['I型', 'II型', 'III型', '总裂隙数'], bottom: 0, textStyle: legendTextStyle },
      series: [
        { name: 'I型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[0]) ?? 0), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: 'II型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[1]) ?? 0), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: 'III型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[2]) ?? 0), itemStyle: { color: GEO_C3, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: '总裂隙数', type: 'bar', data: tableData.value.map(d => {
          const parts = d.type_ratio.split(':')
          const sum = (safeFloat(parts[0]) ?? 0) + (safeFloat(parts[1]) ?? 0) + (safeFloat(parts[2]) ?? 0)
          return sum
        }), itemStyle: { color: GEO_C4, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
      ],
    }
  }

  if (metric === 'node') {
    return {
      ...base,
      legend: { data: ['节点总数', 'X节点', 'Y节点', 'I节点'], bottom: 0, textStyle: legendTextStyle },
      series: [
        { name: '节点总数', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_count) ?? '-'), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: 'X节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[0]) ?? 0), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: 'Y节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[1]) ?? 0), itemStyle: { color: GEO_C3, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
        { name: 'I节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[2]) ?? 0), itemStyle: { color: GEO_C5, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
      ],
    }
  }

  // metric === 'length'
  const series: any[] = [
    { name: '平均迹长', type: 'bar', data: tableData.value.map(d => safeFloat(d.mean_trace_length) ?? '-'), itemStyle: { color: GEO_C2, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() },
  ]
  if (pipelineStore.lastEnableNodeRecognition) {
    series.push({ name: '节点密度', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_density) ?? '-'), itemStyle: { color: GEO_C1, borderRadius: [3, 3, 0, 0] }, ...baseSeriesAnimation() })
  }
  return {
    ...base,
    legend: { data: series.map(s => s.name), bottom: 0, textStyle: legendTextStyle },
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

    // 只保存图片路径；缩略图按需懒加载，避免一次性 base64 加载所有结果图。
    let results = force ? null : cacheStore.getResults()
    if (!results) {
      results = await api.get_results()
      cacheStore.setResults(results!)
    }
    const images: GridImage[] = []
    for (const result of results!) {
      if (result.raw_plot) {
        try {
          images.push({
            outcrop: result.outcrop,
            type: '原始迹线',
            path: result.raw_plot,
            src: '',
          })
        } catch { images.push({ outcrop: result.outcrop, type: '原始迹线', path: result.raw_plot, src: '' }) }
      }
      if (result.rotated_plot) {
        try {
          images.push({
            outcrop: result.outcrop,
            type: '旋转迹线',
            path: result.rotated_plot,
            src: '',
          })
        } catch { images.push({ outcrop: result.outcrop, type: '旋转迹线', path: result.rotated_plot, src: '' }) }
      }
      if (pipelineStore.lastExportRosePlot && result.rose_plot) {
        try {
          images.push({
            outcrop: result.outcrop,
            type: '走向玫瑰',
            path: result.rose_plot,
            src: '',
          })
        } catch { images.push({ outcrop: result.outcrop, type: '走向玫瑰', path: result.rose_plot, src: '' }) }
      }
    }
    allImages.value = images
    prefetchGridImages()
  } catch (e) {
    console.error('对比页加载失败', e)
    msg.error('对比页加载失败')
  } finally {
    loading.value = false
    isLoadingComparison = false
  }
}

onActivated(() => {
  if (!hasInitializedComparison) {
    hasInitializedComparison = true
    loadComparison()
  } else if (!cacheStore.isScanValid) {
    cacheStore.invalidateComparison()
    cacheStore.invalidateResults()
    loadComparison(true)
  } else if (!cacheStore.isComparisonValid || !cacheStore.isResultsValid) {
    if (!cacheStore.isComparisonValid) cacheStore.invalidateComparison()
    if (!cacheStore.isResultsValid) cacheStore.invalidateResults()
    loadComparison(false)
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
  font-size: 13px;
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
  min-height: 168px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--tp-space-4);
  color: var(--tp-brand-accent);
  font-size: 14px;
  background:
    linear-gradient(rgba(2, 132, 199, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(2, 132, 199, 0.035) 1px, transparent 1px);
  background-size: 24px 24px;
  border-radius: var(--tp-radius-md);
}

.loading-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 220px;
  font-family: var(--tp-font-heading);
}

.loading-copy .tp-skeleton-line {
  width: 220px;
}

.loading-copy .tp-skeleton-line.short {
  width: 140px;
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
  font-size: 14px;
  color: var(--tp-text-muted);
}

.chart {
  height: 300px;
  filter: drop-shadow(0 12px 28px rgba(26, 54, 93, 0.06));
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
  background: linear-gradient(180deg, rgba(255,255,255,0.82), var(--tp-bg-sunken));
  border-radius: var(--tp-radius-md);
  overflow: hidden;
  cursor: zoom-in;
  transition: all var(--tp-duration-slow) var(--tp-easing-expo);
  border: 1px solid var(--tp-border-light);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.65);
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
  background:
    linear-gradient(rgba(2, 132, 199, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(2, 132, 199, 0.025) 1px, transparent 1px);
  background-size: 18px 18px;
}

.grid-img {
  max-width: 100%;
  max-height: 160px;
  object-fit: contain;
  transition: transform var(--tp-duration-normal) var(--tp-easing-smooth), filter var(--tp-duration-normal);
}

.image-card:hover .grid-img {
  transform: scale(1.025);
  filter: drop-shadow(0 8px 18px rgba(26, 54, 93, 0.16));
}

.image-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: var(--tp-space-2);
  width: 100%;
  min-height: 96px;
  border: 1px dashed var(--tp-border-medium);
  border-radius: var(--tp-radius-sm);
  color: var(--tp-text-muted);
  font-size: 12px;
  background: var(--tp-bg-base);
}

.image-placeholder.loading {
  color: var(--tp-brand-accent);
  border-color: rgba(56, 189, 248, 0.28);
  background: rgba(2, 132, 199, 0.06);
}

.image-placeholder .tp-loading-orbit {
  width: 24px;
  height: 24px;
}

.image-placeholder .tp-loading-orbit::before {
  inset: 3px;
}

.image-placeholder .tp-loading-orbit::after {
  inset: 9px;
}
</style>
