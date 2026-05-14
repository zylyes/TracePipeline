<template>
  <div class="histogram-chart">
    <v-chart class="chart" :option="option" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, TitleComponent])

const props = defineProps<{
  histogram: {
    bins: number[]
    edges: number[]
  }
}>()

const echartsFont = '"Times New Roman", "SimSun", serif'

const option = computed(() => {
  const edges = props.histogram.edges
  const bins = props.histogram.bins
  const xData = edges.slice(0, -1).map((v, i) => `${v.toFixed(1)}-${edges[i+1].toFixed(1)}`)

  return {
    title: { text: '迹长分布直方图', left: 'center', textStyle: { fontFamily: echartsFont } },
    tooltip: { trigger: 'axis', textStyle: { fontFamily: echartsFont } },
    grid: { left: '10%', right: '10%', bottom: '15%' },
    xAxis: {
      type: 'category',
      data: xData,
      name: '迹长(m)',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: { fontFamily: echartsFont },
      axisLabel: { rotate: 30, fontFamily: echartsFont },
    },
    yAxis: {
      type: 'value',
      name: '频数',
      nameTextStyle: { fontFamily: echartsFont },
      axisLabel: { fontFamily: echartsFont },
    },
    series: [{
      data: bins,
      type: 'bar',
      itemStyle: { color: '#2c3e50' },
      barWidth: '60%',
    }],
  }
})
</script>

<style scoped lang="scss">
.histogram-chart {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.chart {
  height: 300px;
}
</style>
