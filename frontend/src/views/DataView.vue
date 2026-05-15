<template>
  <div class="data-view">
    <h2 class="page-title">数据</h2>
    <div class="toolbar">
      <el-select v-model="selectedOutcrop" placeholder="选择露头" @change="onOutcropChange">
        <el-option v-for="o in outcrops" :key="o" :label="o" :value="o" />
      </el-select>
      <el-tabs v-model="source" type="border-card" class="source-tabs" @tab-change="onSourceChange">
        <el-tab-pane label="输入数据" name="input" />
        <el-tab-pane label="输出数据" name="output" />
      </el-tabs>
    </div>

    <div class="info-card" v-if="basicInfo && source === 'output'">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="测线走向">{{ basicInfo.scanline_azimuth }}°</el-descriptions-item>
        <el-descriptions-item label="迹线条数">{{ basicInfo.trace_count }}</el-descriptions-item>
        <el-descriptions-item label="测线长度">{{ basicInfo.scanline_length }}m</el-descriptions-item>
        <el-descriptions-item label="露头面积">{{ basicInfo.outcrop_area }}m²</el-descriptions-item>
        <el-descriptions-item label="平均迹长">{{ basicInfo.mean_trace_length }}m</el-descriptions-item>
        <el-descriptions-item label="面积来源">{{ formatAreaSource(basicInfo.area_source) }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <DataTable
      v-if="selectedOutcrop"
      :outcrop="selectedOutcrop"
      :source="source"
      :show-node-tabs="pipelineStore.lastEnableNodeRecognition"
      :key="selectedOutcrop + source"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DataTable from '@/components/DataTable.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { api } from '@/api/pywebview'
import { formatAreaSource } from '@/utils/format'
import type { StatsData } from '@/types'

const route = useRoute()
const pipelineStore = usePipelineStore()
const outcrops = ref<string[]>([])
const selectedOutcrop = ref('')
const basicInfo = ref<StatsData | null>(null)

// source 默认为 output，路由参数可覆盖初始值
const source = ref((route.query.source as string) || 'output')

async function loadOutcrops() {
  try {
    const files = await api.scan_files()
    outcrops.value = files.map((f: any) => f.outcrop)

    // 检查路由参数中是否有指定的露头
    const queryOutcrop = route.query.outcrop as string | undefined
    if (queryOutcrop && outcrops.value.includes(queryOutcrop)) {
      selectedOutcrop.value = queryOutcrop
      await onOutcropChange()
      return
    }

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
  if (source.value === 'input') {
    basicInfo.value = null
    return
  }
  try {
    const stats = await api.get_stats(selectedOutcrop.value)
    basicInfo.value = stats
  } catch (e) {
    console.error(e)
    ElMessage.error('加载统计数据失败')
  }
}

function onSourceChange() {
  if (source.value === 'input') {
    basicInfo.value = null
  } else {
    onOutcropChange()
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
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.source-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }
  :deep(.el-tabs__content) {
    display: none;
  }
}
.info-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-bottom: 16px;
}
</style>
