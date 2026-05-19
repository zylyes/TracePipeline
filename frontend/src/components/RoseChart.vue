<template>
  <div class="rose-chart tp-card">
    <div class="rose-toolbar">
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button label="chart">ECharts</el-radio-button>
        <el-radio-button label="image">原始图片</el-radio-button>
      </el-radio-group>
      <el-button v-if="viewMode === 'chart' && hasData" size="small" :icon="Refresh" @click="resetView">重置视角</el-button>
    </div>
    <div v-if="viewMode === 'chart' && hasData" class="chart-hint">滚轮缩放 · 拖拽旋转</div>
    <div
      v-if="viewMode === 'chart' && hasData"
      ref="chartWrapper"
      class="chart-wrapper"
      @wheel.prevent="onWheel"
      @mousedown="onMouseDown"
    >
      <v-chart class="chart" :option="chartOption" autoresize />
    </div>
    <img v-else-if="viewMode === 'image' && roseImageUrl" :src="roseImageUrl" class="rose-image" />
    <el-empty v-else description="暂无玫瑰图数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { PolarComponent, TooltipComponent, TitleComponent } from 'echarts/components'
import { Refresh } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { loadImageBase64 } from '@/utils/image'
import { getEchartsFontFamily, baseTitleStyle, baseTooltipStyle, baseAnimationConfig, baseSeriesAnimation, CHART_COLOR_PRIMARY } from '@/utils/echarts-theme'

use([CanvasRenderer, BarChart, PolarComponent, TooltipComponent, TitleComponent])

const props = defineProps<{
  strikes: number[]
  roseImage?: string
}>()

const viewMode = ref('chart')
const roseImageUrl = ref('')
const chartWrapper = ref<HTMLElement>()

const zoomLevel = ref(1)
const rotationOffset = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)

const hasData = computed(() => props.strikes && props.strikes.length > 0)

watch(() => props.roseImage, async (val) => {
  roseImageUrl.value = val ? await loadImageBase64(val) : ''
}, { immediate: true })

function resetView() {
  zoomLevel.value = 1
  rotationOffset.value = 0
}

function onWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  zoomLevel.value = Math.max(0.5, Math.min(3, zoomLevel.value * delta))
}

function onMouseDown(e: MouseEvent) {
  isDragging.value = true
  dragStartX.value = e.clientX
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  const dx = e.clientX - dragStartX.value
  rotationOffset.value += dx * 0.5
  dragStartX.value = e.clientX
}

function onMouseUp() {
  isDragging.value = false
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

const chartOption = computed(() => {
  if (!hasData.value) return {}

  const binWidth = 10
  const halfBins = new Array(18).fill(0)
  const font = getEchartsFontFamily()
  const cssVar = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || undefined

  props.strikes.forEach(s => {
    const deg = ((s % 180) + 180) % 180
    const idx = Math.min(Math.floor(deg / binWidth), 17)
    halfBins[idx]++
  })

  const data: number[] = []
  const categories: string[] = []
  for (let i = 0; i < 18; i++) {
    data.push(halfBins[i])
    const angle = i * binWidth
    categories.push(angle % 30 === 0 ? `${angle}°` : '')
  }
  for (let i = 0; i < 18; i++) {
    data.push(halfBins[i])
    const angle = i * binWidth + 180
    categories.push(angle % 30 === 0 ? `${angle}°` : '')
  }

  const baseMax = Math.max(...data, 1)
  const maxCount = Math.ceil(baseMax / Math.max(0.2, zoomLevel.value))

  return {
    ...baseAnimationConfig(),
    title: {
      text: '走向玫瑰图',
      left: 'center',
      textStyle: { ...baseTitleStyle() },
    },
    tooltip: {
      trigger: 'item',
      ...baseTooltipStyle(),
      formatter: (params: any) => {
        const idx = params.dataIndex
        const halfIdx = idx % 18
        const start = halfIdx * binWidth + (idx >= 18 ? 180 : 0)
        return `${start}°-${start + binWidth}°: ${params.value} 条`
      }
    },
    polar: {},
    angleAxis: {
      type: 'category',
      data: categories,
      startAngle: 90 + rotationOffset.value,
      axisLabel: {
        fontFamily: font,
        fontSize: 11,
        color: cssVar('--tp-text-secondary') || '#5a5a6e',
      },
      axisLine: { lineStyle: { color: cssVar('--tp-text-tertiary') || '#8a8a9a' } },
      splitLine: { show: true, lineStyle: { color: cssVar('--tp-border') || '#e8eaed' } },
    },
    radiusAxis: {
      min: 0,
      max: maxCount,
      axisLabel: {
        fontFamily: font,
        fontSize: 10,
        color: cssVar('--tp-text-secondary') || '#5a5a6e',
      },
      splitLine: { lineStyle: { color: cssVar('--tp-border') || '#e8eaed' } },
    },
    series: [{
      type: 'bar',
      coordinateSystem: 'polar',
      data: data,
      barWidth: '95%',
      itemStyle: {
        color: CHART_COLOR_PRIMARY,
        opacity: 0.75,
        borderWidth: 0.5,
        borderColor: '#A0503A',
      },
      emphasis: {
        itemStyle: { opacity: 1, color: '#E08A6A' }
      },
      ...baseSeriesAnimation(),
    }],
  }
})
</script>

<style scoped lang="scss">
.rose-chart {
  border: 1px solid var(--tp-border-light);
}
.rose-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.chart-hint {
  text-align: right;
  font-family: var(--tp-font-body);
  font-size: 11px;
  color: var(--tp-text-muted);
  margin-bottom: 4px;
  user-select: none;
}
.chart-wrapper {
  cursor: grab;
}
.chart-wrapper:active {
  cursor: grabbing;
}
.chart {
  height: 420px;
}
.rose-image {
  width: 100%;
  max-height: 420px;
  object-fit: contain;
}
</style>
