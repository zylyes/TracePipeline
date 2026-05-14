<template>
  <div class="pie-chart">
    <v-chart class="chart" :option="option" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent, TitleComponent])

const props = defineProps<{
  typeCounts: {
    type_i: number
    type_ii: number
    type_iii: number
  }
}>()

const echartsFont = '"Times New Roman", "SimSun", serif'

const option = computed(() => ({
  title: { text: 'I/II/III 型分类', left: 'center', textStyle: { fontFamily: echartsFont } },
  tooltip: { trigger: 'item', textStyle: { fontFamily: echartsFont } },
  legend: { bottom: '0%', left: 'center', textStyle: { fontFamily: echartsFont } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
    label: { show: true, formatter: '{b}: {c}', fontFamily: echartsFont },
    data: [
      { value: props.typeCounts.type_i, name: 'I型', itemStyle: { color: '#2E7D5A' } },
      { value: props.typeCounts.type_ii, name: 'II型', itemStyle: { color: '#2c3e50' } },
      { value: props.typeCounts.type_iii, name: 'III型', itemStyle: { color: '#B85C38' } },
    ],
  }],
}))
</script>

<style scoped lang="scss">
.pie-chart {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.chart {
  height: 300px;
}
</style>
