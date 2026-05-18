<template>
  <div class="pie-chart tp-card">
    <v-chart class="chart" :option="option" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart as PieChartType } from 'echarts/charts'
import { TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { getEchartsFontFamily, baseTitleStyle, baseTooltipStyle, baseAnimationConfig, CHART_COLOR_TERTIARY, CHART_COLOR_SECONDARY, CHART_COLOR_PRIMARY } from '@/utils/echarts-theme'

use([CanvasRenderer, PieChartType, TooltipComponent, LegendComponent, TitleComponent])

const props = defineProps<{
  typeCounts: {
    type_i: number
    type_ii: number
    type_iii: number
  }
}>()

const option = computed(() => {
  const font = getEchartsFontFamily()
  return {
    ...baseAnimationConfig(),
    title: { text: 'I/II/III 型分类', left: 'center', textStyle: { ...baseTitleStyle(), fontSize: 14 } },
    tooltip: { trigger: 'item', ...baseTooltipStyle() },
    legend: { bottom: '0%', left: 'center', textStyle: { fontFamily: font, fontSize: 12, color: '#5a5a6e' } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#ffffff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {c}', fontFamily: font, color: '#1a1a2e' },
      data: [
        { value: props.typeCounts.type_i, name: 'I型', itemStyle: { color: CHART_COLOR_TERTIARY } },
        { value: props.typeCounts.type_ii, name: 'II型', itemStyle: { color: CHART_COLOR_SECONDARY } },
        { value: props.typeCounts.type_iii, name: 'III型', itemStyle: { color: CHART_COLOR_PRIMARY } },
      ],
    }],
  }
})
</script>

<style scoped lang="scss">
.pie-chart {
  border: 1px solid var(--tp-border-light);
}
.chart {
  height: 300px;
}
</style>
