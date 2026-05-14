<template>
  <div class="comparison-view">
    <h2 class="page-title">对比</h2>
    <el-table :data="tableData" size="small" style="width: 100%" v-loading="loading">
      <el-table-column prop="outcrop" label="露头" width="80" />
      <el-table-column prop="p10" label="P10" />
      <el-table-column prop="p20" label="P20" />
      <el-table-column prop="p21" label="P21" />
      <el-table-column prop="mean_trace_length" label="平均迹长" />
      <el-table-column prop="scanline_azimuth" label="走向" />
      <el-table-column prop="type_ratio" label="I:II:III" />
    </el-table>

    <div class="chart-area">
      <v-chart class="chart" :option="barOption" autoresize />
    </div>

    <ImageGrid :images="gridImages" />
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
import ImageGrid from '@/components/ImageGrid.vue'
import { api } from '@/api/pywebview'
import type { ComparisonRow } from '@/types'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const tableData = ref<ComparisonRow[]>([])
const gridImages = ref<any[]>([])
const loading = ref(false)

const echartsFont = '"Times New Roman", "SimSun", serif'

const barOption = computed(() => {
  const outcrops = tableData.value.map(d => d.outcrop)
  return {
    title: { text: '多露头参数对比', left: 'center', textStyle: { fontFamily: echartsFont } },
    tooltip: { trigger: 'axis', textStyle: { fontFamily: echartsFont } },
    legend: { data: ['P10', 'P20', 'P21'], bottom: 0, textStyle: { fontFamily: echartsFont } },
    grid: { left: '10%', right: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: outcrops, axisLabel: { fontFamily: echartsFont } },
    yAxis: { type: 'value', axisLabel: { fontFamily: echartsFont } },
    series: [
      { name: 'P10', type: 'bar', data: tableData.value.map(d => parseFloat(d.p10) || 0), itemStyle: { color: '#2c3e50' } },
      { name: 'P20', type: 'bar', data: tableData.value.map(d => parseFloat(d.p20) || 0), itemStyle: { color: '#B85C38' } },
      { name: 'P21', type: 'bar', data: tableData.value.map(d => parseFloat(d.p21) || 0), itemStyle: { color: '#2E7D5A' } },
    ],
  }
})

async function loadComparison() {
  loading.value = true
  try {
    const files = await api.scan_files()
    const outcrops = files.map((f: any) => f.outcrop)
    if (outcrops.length === 0) {
      tableData.value = []
      gridImages.value = []
      return
    }
    const data = await api.get_comparison(outcrops)
    tableData.value = data.map((d: any) => ({
      outcrop: d.outcrop,
      p10: d.p10 != null ? Number(d.p10).toFixed(2) : '—',
      p20: d.p20 != null ? Number(d.p20).toFixed(2) : '—',
      p21: d.p21 != null ? Number(d.p21).toFixed(2) : '—',
      mean_trace_length: d.mean_trace_length != null ? Number(d.mean_trace_length).toFixed(2) + 'm' : '—',
      scanline_azimuth: (d.scanline_azimuth ?? '—') + '°',
      type_ratio: `${d.type_i ?? 0}:${d.type_ii ?? 0}:${d.type_iii ?? 0}`,
    }))

    const results = await api.get_results()
    gridImages.value = results.map((r: any) => ({
      key: r.outcrop,
      src: r.raw_plot || '',
      label: r.outcrop,
    })).filter((r: any) => r.src)
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
.chart {
  height: 300px;
}
</style>
