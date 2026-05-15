<template>
  <div class="comparison-view">
    <h2 class="page-title">对比</h2>

    <el-empty v-if="!loading && tableData.length === 0" description="暂无露头数据" />

    <el-table :data="tableData" size="small" style="width: 100%" v-loading="loading" v-else>
      <el-table-column prop="outcrop" label="露头" width="80" />
      <el-table-column prop="trace_count" label="迹线数" />
      <el-table-column prop="p10" label="P10" />
      <el-table-column prop="p20" label="P20" />
      <el-table-column prop="p21" label="P21" />
      <el-table-column prop="mean_trace_length" label="平均迹长(m)" />
      <el-table-column prop="scanline_azimuth" label="走向" />
      <el-table-column prop="type_ratio" label="I:II:III" />
      <el-table-column v-if="pipelineStore.lastEnableNodeRecognition" prop="node_count" label="节点总数" />
      <el-table-column v-if="pipelineStore.lastEnableNodeRecognition" prop="node_ratio" label="X:Y:I" />
      <el-table-column v-if="pipelineStore.lastEnableNodeRecognition" prop="node_density" label="节点密度" />
    </el-table>

    <div class="chart-area" v-if="tableData.length > 0">
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
    <div class="images-panel" v-if="allImages.length > 0">
      <h3>处理结果图</h3>
      <div class="image-grid">
        <div
          class="image-card"
          v-for="(img, idx) in allImages"
          :key="img.outcrop + img.type"
          @click="openViewer(idx)"
        >
          <div class="image-label">{{ img.outcrop }} · {{ img.type }}</div>
          <div class="image-wrapper">
            <img :src="img.src" class="grid-img" />
          </div>
        </div>
      </div>
    </div>
    <el-empty v-else-if="!loading" description="暂无图片" style="margin-top:16px" />

    <ImageViewer
      v-model:visible="viewerVisible"
      :images="viewerImages"
      :initial-index="viewerInitialIndex"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import ImageViewer from '@/components/ImageViewer.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { api } from '@/api/pywebview'
import { loadImageBase64 } from '@/utils/image'
import type { ComparisonRow, PipelineResult } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const pipelineStore = usePipelineStore()

const tableData = ref<ComparisonRow[]>([])
const loading = ref(false)
const chartMetric = ref('density')

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

function openViewer(index: number) {
  viewerImages.value = allImages.value.map(img => ({
    title: `${img.outcrop} · ${img.type}`,
    src: img.src,
  }))
  viewerInitialIndex.value = index
  viewerVisible.value = true
}

function safeFloat(val: string): number | null {
  if (val === '—' || val == null || val === '') return null
  const n = parseFloat(val)
  return isNaN(n) ? null : n
}

const echartsFont = '"Times New Roman", "SimSun", serif'

const barOption = computed(() => {
  const outcrops = tableData.value.map(d => d.outcrop)
  const metric = chartMetric.value

  const base = {
    title: { text: '多露头参数对比', left: 'center', textStyle: { fontFamily: echartsFont } },
    tooltip: { trigger: 'axis', textStyle: { fontFamily: echartsFont } },
    legend: { bottom: 0, textStyle: { fontFamily: echartsFont } },
    grid: { left: '10%', right: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: outcrops, axisLabel: { fontFamily: echartsFont } },
    yAxis: { type: 'value', axisLabel: { fontFamily: echartsFont } },
  }

  if (metric === 'density') {
    return {
      ...base,
      legend: { data: ['P10', 'P20', 'P21'], bottom: 0, textStyle: { fontFamily: echartsFont } },
      series: [
        { name: 'P10', type: 'bar', data: tableData.value.map(d => safeFloat(d.p10) ?? '-'), itemStyle: { color: '#2c3e50' } },
        { name: 'P20', type: 'bar', data: tableData.value.map(d => safeFloat(d.p20) ?? '-'), itemStyle: { color: '#B85C38' } },
        { name: 'P21', type: 'bar', data: tableData.value.map(d => safeFloat(d.p21) ?? '-'), itemStyle: { color: '#2E7D5A' } },
      ],
    }
  }

  if (metric === 'type') {
    return {
      ...base,
      legend: { data: ['I型', 'II型', 'III型'], bottom: 0, textStyle: { fontFamily: echartsFont } },
      series: [
        { name: 'I型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[0]) ?? 0), itemStyle: { color: '#2c3e50' } },
        { name: 'II型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[1]) ?? 0), itemStyle: { color: '#B85C38' } },
        { name: 'III型', type: 'bar', data: tableData.value.map(d => safeFloat(d.type_ratio.split(':')[2]) ?? 0), itemStyle: { color: '#2E7D5A' } },
      ],
    }
  }

  if (metric === 'node') {
    return {
      ...base,
      legend: { data: ['节点总数', 'X节点', 'Y节点', 'I节点'], bottom: 0, textStyle: { fontFamily: echartsFont } },
      series: [
        { name: '节点总数', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_count) ?? '-'), itemStyle: { color: '#2c3e50' } },
        { name: 'X节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[0]) ?? 0), itemStyle: { color: '#B85C38' } },
        { name: 'Y节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[1]) ?? 0), itemStyle: { color: '#2E7D5A' } },
        { name: 'I节点', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_ratio.split(':')[2]) ?? 0), itemStyle: { color: '#7B1FA2' } },
      ],
    }
  }

  // metric === 'length'
  const series: any[] = [
    { name: '平均迹长', type: 'bar', data: tableData.value.map(d => safeFloat(d.mean_trace_length) ?? '-'), itemStyle: { color: '#2c3e50' } },
  ]
  if (pipelineStore.lastEnableNodeRecognition) {
    series.push({ name: '节点密度', type: 'bar', data: tableData.value.map(d => safeFloat(d.node_density) ?? '-'), itemStyle: { color: '#B85C38' } })
  }
  return {
    ...base,
    legend: { data: series.map(s => s.name), bottom: 0, textStyle: { fontFamily: echartsFont } },
    series,
  }
})

async function loadComparison() {
  loading.value = true
  try {
    const files = await api.scan_files()
    const outcrops = files.map((f: any) => f.outcrop)
    if (outcrops.length === 0) {
      tableData.value = []
      allImages.value = []
      return
    }
    const data = await api.get_comparison(outcrops)
    tableData.value = data.map((d: any) => {
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

    // 加载所有露头的所有图片
    const results = await api.get_results()
    const images: GridImage[] = []
    for (const result of results) {
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
  }
}

onMounted(loadComparison)
</script>

<style scoped lang="scss">
.comparison-view {
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
.chart-area {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-top: 16px;
}
.chart-toolbar {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}
.chart {
  height: 300px;
}
.images-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-top: 16px;
}
.images-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
.image-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.image-card {
  background: #f5f7fa;
  border-radius: 6px;
  overflow: hidden;
  cursor: zoom-in;
  transition: all 0.2s;
}
.image-card:hover {
  box-shadow: 0 4px 12px 0 rgba(0,0,0,0.12);
  transform: translateY(-2px);
}
.image-label {
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 600;
  color: #2c3e50;
  background: #e4e7ed;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
