<template>
  <div class="rose-chart">
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

use([CanvasRenderer, BarChart, PolarComponent, TooltipComponent, TitleComponent])

const props = defineProps<{
  strikes: number[]
  roseImage?: string
}>()

const viewMode = ref('chart')
const roseImageUrl = ref('')
const chartWrapper = ref<HTMLElement>()

// 视图交互状态
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

  // 分箱：走向折叠到半圆 [0, 180)
  props.strikes.forEach(s => {
    const deg = ((s % 180) + 180) % 180
    const idx = Math.min(Math.floor(deg / binWidth), 17)
    halfBins[idx]++
  })

  // 构建 36 个类目的数据（0-180° 和 180-360° 镜像对称）
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
  // zoomLevel 只影响显示范围，不改变数据本身
  const maxCount = Math.ceil(baseMax / Math.max(0.2, zoomLevel.value))

  return {
    title: {
      text: '走向玫瑰图',
      left: 'center',
      textStyle: { fontFamily: '"Times New Roman", "SimSun", serif', fontSize: 16 }
    },
    tooltip: {
      trigger: 'item',
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
        fontFamily: '"Times New Roman", serif',
        fontSize: 11,
        color: '#666',
      },
      axisLine: { lineStyle: { color: '#999' } },
      splitLine: { show: true, lineStyle: { color: '#e0e0e0' } },
    },
    radiusAxis: {
      min: 0,
      max: maxCount,
      axisLabel: {
        fontFamily: '"Times New Roman", serif',
        fontSize: 10,
        color: '#666',
      },
      splitLine: { lineStyle: { color: '#e0e0e0' } },
    },
    series: [{
      type: 'bar',
      coordinateSystem: 'polar',
      data: data,
      barWidth: '95%',
      itemStyle: {
        color: '#C94C4C',
        opacity: 0.75,
        borderWidth: 0.5,
        borderColor: '#7A1F1F',
      },
      emphasis: {
        itemStyle: { opacity: 1, color: '#B85C38' }
      },
    }],
  }
})
</script>

<style scoped lang="scss">
.rose-chart {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.rose-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.chart-hint {
  text-align: right;
  font-size: 11px;
  color: #909399;
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
