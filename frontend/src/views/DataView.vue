<template>
  <div class="data-view">
    <h2 class="page-title">数据</h2>
    <div class="toolbar">
      <el-select v-model="selectedOutcrop" placeholder="选择露头" @change="onOutcropChange">
        <el-option v-for="o in outcrops" :key="o" :label="o" :value="o" />
      </el-select>
    </div>

    <div class="info-card" v-if="basicInfo">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="测线走向">{{ basicInfo.scanline_azimuth }}°</el-descriptions-item>
        <el-descriptions-item label="迹线条数">{{ basicInfo.trace_count }}</el-descriptions-item>
        <el-descriptions-item label="测线长度">{{ basicInfo.scanline_length }}m</el-descriptions-item>
        <el-descriptions-item label="露头面积">{{ basicInfo.outcrop_area }}m²</el-descriptions-item>
        <el-descriptions-item label="平均迹长">{{ basicInfo.mean_trace_length }}m</el-descriptions-item>
        <el-descriptions-item label="面积来源">{{ basicInfo.area_source }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <DataTable v-if="selectedOutcrop" :outcrop="selectedOutcrop" :key="selectedOutcrop" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import DataTable from '@/components/DataTable.vue'
import { api } from '@/api/pywebview'
import type { StatsData } from '@/types'

const outcrops = ref<string[]>([])
const selectedOutcrop = ref('')
const basicInfo = ref<StatsData | null>(null)

async function loadOutcrops() {
  try {
    const files = await api.scan_files()
    outcrops.value = files.map((f: any) => f.outcrop)
    if (outcrops.value.length && !selectedOutcrop.value) {
      selectedOutcrop.value = outcrops.value[0]
      await onOutcropChange()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载露头列表失败')
  }
}

async function onOutcropChange() {
  if (!selectedOutcrop.value) return
  try {
    const stats = await api.get_stats(selectedOutcrop.value)
    basicInfo.value = stats
  } catch (e) {
    console.error(e)
    ElMessage.error('加载统计数据失败')
  }
}

onMounted(async () => {
  await loadOutcrops()
})
</script>

<style scoped lang="scss">
.data-view {
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
  margin-bottom: 16px;
}
.info-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-bottom: 16px;
}
</style>
