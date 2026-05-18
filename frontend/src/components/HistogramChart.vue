<template>
  <div class="histogram-chart tp-card">
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
import { getEchartsFontFamily, baseTitleStyle, baseAxisLabelStyle, baseTooltipStyle, baseAnimationConfig, baseSeriesAnimation, CHART_COLOR_SECONDARY } from '@/utils/echarts-theme'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, TitleComponent])

const props = defineProps<{
  histogram: {
    bins: number[]
    edges: number[]
  }
}>()

const option = computed(() => {
  const edges = props.histogram.edges
  const bins = props.histogram.bins
  const xData = edges.slice(0, -1).map((v, i) => `${v.toFixed(1)}-${edges[i+1].toFixed(1)}`)
  const font = getEchartsFontFamily()

  return {
    ...baseAnimationConfig(),
    title: { text: '迹长分布直方图', left: 'center', textStyle: { ...baseTitleStyle(), fontSize: 14 } },
    tooltip: { trigger: 'axis', ...baseTooltipStyle() },
    grid: { left: '10%', right: '10%', bottom: '24%' },
    xAxis: {
      type: 'category',
      data: xData,
      name: '迹长(m)',
      nameLocation: 'middle',
      nameGap: 38,
      nameTextStyle: { fontFamily: font },
      axisLabel: { rotate: 40, fontSize: 10, fontFamily: font, color: '#5a5a6e' },
    },
    yAxis: {
      type: 'value',
      name: '频数',
      nameTextStyle: { fontFamily: font },
      axisLabel: { ...baseAxisLabelStyle() },
    },
    series: [{
      data: bins,
      type: 'bar',
      itemStyle: { color: CHART_COLOR_SECONDARY },
      barWidth: '60%',
      ...baseSeriesAnimation(),
    }],
  }
})
</script>

<style scoped lang="scss">
.histogram-chart {
  border: 1px solid var(--tp-border-light);
}
.chart {
  height: 300px;
}
</style>
