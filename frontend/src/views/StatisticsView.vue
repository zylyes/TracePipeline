<template>
  <div class="statistics-view">
    <h2 class="page-title">统计</h2>
    <div class="toolbar">
      <el-select v-model="selectedOutcrop" placeholder="选择露头" @change="loadStats">
        <el-option v-for="o in outcrops" :key="o" :label="o" :value="o" />
      </el-select>
      <el-button :icon="Document" @click="exportReport">导出统计报告</el-button>
    </div>

    <StatCards :stats="stats" />

    <div class="charts-row">
      <HistogramChart :histogram="stats.histogram || { bins: [], edges: [] }" />
      <PieChart :type-counts="{ type_i: stats.type_i || 0, type_ii: stats.type_ii || 0, type_iii: stats.type_iii || 0 }" />
    </div>

    <RoseChart :strikes="roseStrikes" :rose-image="roseImage" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import StatCards from '@/components/StatCards.vue'
import HistogramChart from '@/components/HistogramChart.vue'
import PieChart from '@/components/PieChart.vue'
import RoseChart from '@/components/RoseChart.vue'
import { api } from '@/api/pywebview'

const outcrops = ref<string[]>([])
const selectedOutcrop = ref('')
const stats = ref<any>({})
const roseImage = ref('')

const roseStrikes = computed(() => {
  return stats.value.strikes || []
})

async function loadOutcrops() {
  try {
    const files = await api.scan_files()
    outcrops.value = files.map((f: any) => f.outcrop)
    if (outcrops.value.length && !selectedOutcrop.value) {
      selectedOutcrop.value = outcrops.value[0]
      await loadStats()
    }
  } catch (e) {
    ElMessage.error('加载露头列表失败')
  }
}

async function loadStats() {
  if (!selectedOutcrop.value) return
  stats.value = {}
  roseImage.value = ''
  try {
    const res = await api.get_stats(selectedOutcrop.value)
    if (res.error) {
      ElMessage.error(res.error)
      return
    }
    stats.value = res
    const results = await api.get_results()
    const match = results.find((r: any) => r.outcrop === selectedOutcrop.value)
    if (match && match.rose_plot) {
      roseImage.value = match.rose_plot
    }
  } catch (e) {
    ElMessage.error('加载统计失败')
  }
}

function exportReport() {
  ElMessage.info('报告导出功能开发中')
}

onMounted(loadOutcrops)
</script>

<style scoped lang="scss">
.statistics-view {
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
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
</style>
