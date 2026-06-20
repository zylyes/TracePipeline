<template>
  <div class="data-view">
    <h2 class="page-title">数据</h2>
    <div class="toolbar">
      <el-select v-model="selectedOutcrop" placeholder="选择露头" @change="() => onOutcropChange()" size="small">
        <el-option v-for="o in outcrops" :key="o" :label="o" :value="o" />
      </el-select>
      <el-tabs v-model="source" class="modern-tabs compact" @tab-change="onSourceChange">
        <el-tab-pane label="输入数据" name="input" />
        <el-tab-pane label="输出数据" name="output" />
      </el-tabs>
    </div>

    <div class="info-card tp-card" v-if="basicInfo && source === 'output'">
      <div class="info-header">
        <div class="info-header-left">
          <div class="info-icon">
            <el-icon :size="14"><InfoFilled /></el-icon>
          </div>
          <span class="info-title">露头基本信息</span>
        </div>
      </div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="测线走向">
          <span class="tp-data">{{ basicInfo.scanline_azimuth }}°</span>
        </el-descriptions-item>
        <el-descriptions-item label="迹线条数">
          <span class="tp-data">{{ basicInfo.trace_count }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="测线长度">
          <span class="tp-data">{{ basicInfo.scanline_length }}m</span>
        </el-descriptions-item>
        <el-descriptions-item label="露头面积">
          <span class="tp-data">{{ basicInfo.outcrop_area }}m²</span>
        </el-descriptions-item>
        <el-descriptions-item label="平均迹长">
          <span class="tp-data">{{ basicInfo.mean_trace_length }}m</span>
        </el-descriptions-item>
        <el-descriptions-item label="面积来源">
          <span>{{ formatAreaSource(basicInfo.area_source) }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="table-container" v-if="selectedOutcrop">
      <DataTable
        :outcrop="selectedOutcrop"
        :source="source"
        :show-node-tabs="pipelineStore.lastEnableNodeRecognition"
        :key="selectedOutcrop + source"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { msg } from '@/utils/message'
import { InfoFilled } from '@element-plus/icons-vue'
import DataTable from '@/components/DataTable.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useCacheStore } from '@/stores/cache'
import { api } from '@/api/pywebview'
import { formatAreaSource } from '@/utils/format'
import type { StatsData } from '@/types'

defineOptions({ name: 'Data' })

const route = useRoute()
const pipelineStore = usePipelineStore()
const cacheStore = useCacheStore()
const outcrops = ref<string[]>([])
const selectedOutcrop = ref('')
const basicInfo = ref<StatsData | null>(null)

// source 默认为 output，路由参数可覆盖初始值
const source = ref((route.query.source as string) || 'output')

async function loadOutcrops(force = false) {
  try {
    let files = force ? null : cacheStore.getScan()
    if (!files) {
      files = (await api.scan_files(force)) as any[]
      cacheStore.setScan(files)
    }
    outcrops.value = files!.map((f: any) => f.outcrop)

    // 检查路由参数中是否有指定的露头
    const queryOutcrop = route.query.outcrop as string | undefined
    if (queryOutcrop && outcrops.value.includes(queryOutcrop)) {
      selectedOutcrop.value = queryOutcrop
      await onOutcropChange(force)
      return
    }

    if (outcrops.value.length && !selectedOutcrop.value) {
      selectedOutcrop.value = outcrops.value[0]
    }
    if (selectedOutcrop.value) {
      await onOutcropChange(force)
    }
  } catch (e) {
    console.error(e)
    msg.error('加载露头列表失败')
  }
}

let isLoadingData = false
let hasInitializedData = false

async function onOutcropChange(force = false) {
  if (!selectedOutcrop.value) return
  if (isLoadingData) {
    return
  }
  isLoadingData = true
  if (source.value === 'input') {
    basicInfo.value = null
    isLoadingData = false
    return
  }
  try {
    let stats = force ? null : cacheStore.getStats(selectedOutcrop.value)
    if (!stats) {
      const fetched = (await api.get_stats(selectedOutcrop.value)) as any
      if (fetched && !fetched.error) {
        cacheStore.setStats(selectedOutcrop.value, fetched as any)
        stats = fetched
      } else {
        stats = fetched
      }
    }
    basicInfo.value = stats as StatsData | null
  } catch (e) {
    console.error(e)
    msg.error('加载统计数据失败')
  } finally {
    isLoadingData = false
  }
}

function onSourceChange() {
  if (source.value === 'input') {
    basicInfo.value = null
  } else {
    onOutcropChange()
  }
}

onActivated(() => {
  if (!hasInitializedData) {
    hasInitializedData = true
    loadOutcrops()
    return
  }

  // 同步路由 query：从处理页"预览数据"跳转时携带新的 outcrop/source
  const querySource = route.query.source as string | undefined
  if (querySource && querySource !== source.value) {
    source.value = querySource
  }
  const queryOutcrop = route.query.outcrop as string | undefined

  if (!cacheStore.isScanValid) {
    loadOutcrops(true)
    return
  }

  // scan 缓存有效：若 query 指定了新露头则切换,否则刷新当前源
  if (queryOutcrop && outcrops.value.includes(queryOutcrop) && queryOutcrop !== selectedOutcrop.value) {
    selectedOutcrop.value = queryOutcrop
  }
  if (source.value === 'input') {
    basicInfo.value = null
  } else if (selectedOutcrop.value) {
    onOutcropChange()
  }
})
</script>

<style scoped lang="scss">
.data-view {
  padding: var(--tp-space-5) var(--tp-space-6);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.page-title {
  font-family: var(--tp-font-heading);
  font-size: 22px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin-bottom: var(--tp-space-4);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: var(--tp-space-4);
  margin-bottom: var(--tp-space-4);
  flex-wrap: wrap;
}

/* ── 现代标签页 ── */
.modern-tabs.compact {
  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }

  :deep(.el-tabs__content) {
    display: none;
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }

  :deep(.el-tabs__item) {
    font-family: var(--tp-font-heading);
    font-size: 13px;
    color: var(--tp-text-tertiary);
    padding: 0 16px;
    height: 32px;
    line-height: 32px;
    transition: all var(--tp-duration-normal);
    border-bottom: 2px solid transparent;
  }

  :deep(.el-tabs__item:hover) {
    color: var(--tp-text-secondary);
  }

  :deep(.el-tabs__item.is-active) {
    color: var(--tp-brand-accent);
    border-bottom-color: var(--tp-brand-accent);
    font-weight: 600;
  }

  :deep(.el-tabs__active-bar) {
    display: none;
  }
}

/* ── 信息卡片 ── */
.info-card {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-bottom: var(--tp-space-4);
}

.info-header {
  display: flex;
  align-items: center;
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}

.info-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-info-bg);
  color: var(--tp-info);
}

.info-title {
  font-family: var(--tp-font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text-primary);
}

.info-card :deep(.el-descriptions__label) {
  font-family: var(--tp-font-heading);
  font-weight: 500;
  color: var(--tp-text-secondary);
}

.info-card :deep(.el-descriptions__content) {
  font-family: var(--tp-font-data);
}
</style>
