<template>
  <div class="statistics-view">
    <h2 class="page-title">统计</h2>
    <div class="toolbar">
      <el-select v-model="selectedOutcrop" placeholder="选择露头" @change="() => loadStats()" size="small">
        <el-option v-for="o in outcrops" :key="o" :label="o" :value="o" />
      </el-select>
      <el-button :icon="Document" :loading="exportLoading" @click="exportReport" size="small" type="primary" plain>导出统计报告</el-button>
    </div>

    <!-- 统计警告 -->
    <el-alert
      v-if="alertMessage"
      :title="alertMessage"
      :type="alertType"
      :closable="false"
      show-icon
      class="stats-warning"
    />

    <StatCards :stats="stats" :show-nodes="pipelineStore.lastEnableNodeRecognition" />

    <div class="charts-row">
      <HistogramChart :histogram="stats.histogram || { bins: [], edges: [] }" />
      <PieChart :type-counts="{ type_i: stats.type_i || 0, type_ii: stats.type_ii || 0, type_iii: stats.type_iii || 0 }" />
    </div>

    <!-- 三图切换展示区 -->
    <div class="images-panel tp-card">
      <div class="images-header">
        <div class="images-header-left">
          <div class="images-icon">
            <el-icon :size="16"><Picture /></el-icon>
          </div>
          <h3>处理结果图</h3>
        </div>
      </div>
      <el-tabs v-model="activeImageTab" class="modern-tabs">
        <el-tab-pane label="原始迹线图" name="raw">
          <div class="image-viewport">
            <img
              v-if="rawImageUrl"
              :src="rawImageUrl"
              class="plot-img"
              @click="openViewer(0)"
            />
            <el-empty v-else description="暂无原始迹线图" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="旋转迹线图" name="rotated">
          <div class="image-viewport">
            <img
              v-if="rotatedImageUrl"
              :src="rotatedImageUrl"
              class="plot-img"
              @click="openViewer(1)"
            />
            <el-empty v-else description="暂无旋转迹线图" />
          </div>
        </el-tab-pane>

        <el-tab-pane v-if="pipelineStore.lastExportRosePlot" label="走向玫瑰图" name="rose">
          <div class="image-viewport">
            <img
              v-if="roseImageUrl"
              :src="roseImageUrl"
              class="plot-img"
              @click="openViewer(2)"
            />
            <el-empty v-else description="暂无玫瑰图" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <ImageViewer
      v-model:visible="viewerVisible"
      :images="viewerImages"
      :initial-index="viewerInitialIndex"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated } from 'vue'
import { Document, Picture } from '@element-plus/icons-vue'
import { msg } from '@/utils/message'
import StatCards from '@/components/StatCards.vue'
import HistogramChart from '@/components/HistogramChart.vue'
import PieChart from '@/components/PieChart.vue'
import ImageViewer from '@/components/ImageViewer.vue'
import { usePipelineStore } from '@/stores/pipeline'
import { useCacheStore } from '@/stores/cache'
import { api } from '@/api/pywebview'
import { loadImageBase64 } from '@/utils/image'

defineOptions({ name: 'Statistics' })

const pipelineStore = usePipelineStore()
const cacheStore = useCacheStore()

const outcrops = ref<string[]>([])
const selectedOutcrop = ref('')
const stats = ref<any>({})

const alertType = computed<'success' | 'warning' | 'error'>(() => {
  const source = stats.value?.area_source
  if (source === 'hull_buffered') return 'warning'
  if (source === 'window_equivalent') return 'error'
  return 'success'
})

const alertMessage = computed<string>(() => {
  const source = stats.value?.area_source
  const warning = stats.value?.warning
  if (source === 'hull_buffered') return warning || '面积来源已更换至缓冲凸包'
  if (source === 'window_equivalent') return warning || '面积来源已更换至圆窗等效面积'
  if (source === 'hull' && warning) return warning
  if (warning) return warning
  return ''
})

// 图片 URL
const rawImageUrl = ref('')
const rotatedImageUrl = ref('')
const roseImageUrl = ref('')

// 当前激活的 tab
const activeImageTab = ref('raw')

// 图片查看器
const viewerVisible = ref(false)
const viewerImages = ref<Array<{ title: string; src: string }>>([])
const viewerInitialIndex = ref(0)

async function loadOutcrops(force = false) {
  if (isLoadingOutcrops) {
    console.warn('[StatisticsView] loadOutcrops 被重复调用，已忽略')
    return
  }
  isLoadingOutcrops = true
  try {
    let files = force ? null : cacheStore.getScan()
    if (!files) {
      files = await api.scan_files(force)
      cacheStore.setScan(files!)
    }
    outcrops.value = files!.map((f: any) => f.outcrop)
    if (outcrops.value.length && !selectedOutcrop.value) {
      selectedOutcrop.value = outcrops.value[0]
    }
    if (selectedOutcrop.value) {
      await loadStats(force)
    }
  } catch (e) {
    msg.error('加载露头列表失败')
  } finally {
    isLoadingOutcrops = false
  }
}

let isLoadingOutcrops = false
let isLoadingStats = false
let hasInitializedStats = false

async function loadStats(force = false) {
  if (!selectedOutcrop.value) return
  if (isLoadingStats) {
    console.warn('[StatisticsView] loadStats 被重复调用，已忽略')
    return
  }
  isLoadingStats = true
  stats.value = {}
  rawImageUrl.value = ''
  rotatedImageUrl.value = ''
  roseImageUrl.value = ''

  try {
    let res = force ? null : cacheStore.getStats(selectedOutcrop.value)
    if (!res) {
      res = await api.get_stats(selectedOutcrop.value)
      if (!res.error) {
        cacheStore.setStats(selectedOutcrop.value, res)
      }
    }
    if (res.error) {
      msg.error(res.error)
      return
    }
    stats.value = res

    // 扫描 output 目录获取图片路径（结果列表也走缓存）
    let results = force ? null : cacheStore.getResults()
    if (!results) {
      results = await api.get_results()
      cacheStore.setResults(results!)
    }
    const match = results!.find((r: any) => r.outcrop === selectedOutcrop.value)
    if (match) {
      if (match.raw_plot) {
        rawImageUrl.value = await loadImageBase64(match.raw_plot)
      }
      if (match.rotated_plot) {
        rotatedImageUrl.value = await loadImageBase64(match.rotated_plot)
      }
      if (pipelineStore.lastExportRosePlot && match.rose_plot) {
        roseImageUrl.value = await loadImageBase64(match.rose_plot)
      }
    }
  } catch (e) {
    msg.error('加载统计失败')
  } finally {
    isLoadingStats = false
  }
}

function openViewer(index: number) {
  const images = []
  if (rawImageUrl.value) images.push({ title: '原始迹线图', src: rawImageUrl.value })
  if (rotatedImageUrl.value) images.push({ title: '旋转迹线图', src: rotatedImageUrl.value })
  if (pipelineStore.lastExportRosePlot && roseImageUrl.value) images.push({ title: '走向玫瑰图', src: roseImageUrl.value })
  viewerImages.value = images
  viewerInitialIndex.value = index
  viewerVisible.value = true
}

const exportLoading = ref(false)

async function exportReport() {
  if (!selectedOutcrop.value) {
    msg.warning('请先选择一个露头')
    return
  }
  exportLoading.value = true
  try {
    const res = await api.generate_report(selectedOutcrop.value, 'full', 'both')
    if (res.error) {
      msg.error(res.error)
      return
    }
    const paths: string[] = []
    if (res.docx) paths.push(res.docx)
    if (res.pdf) paths.push(res.pdf)
    if (paths.length) {
      msg.success(`统计报告已导出: ${paths.join(', ')}`)
    } else {
      msg.warning('未生成任何报告文件')
    }
  } catch (e) {
    msg.error('导出统计报告失败')
    console.error(e)
  } finally {
    exportLoading.value = false
  }
}

// KeepAlive 激活时，若缓存已失效则刷新数据
onActivated(() => {
  if (!hasInitializedStats) {
    hasInitializedStats = true
    loadOutcrops()
  } else if (!cacheStore.isScanValid) {
    cacheStore.invalidateStats()
    loadOutcrops(true)
  } else if (!cacheStore.isResultsValid && selectedOutcrop.value) {
    cacheStore.invalidateResults()
    loadStats(false)
  }
})
</script>

<style scoped lang="scss">
.statistics-view {
  padding: var(--tp-space-5) var(--tp-space-6);
  height: 100%;
  overflow-y: auto;
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
  gap: var(--tp-space-3);
  margin-bottom: var(--tp-space-4);
  align-items: center;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--tp-space-4);
  margin-bottom: var(--tp-space-4);
}

.stats-warning {
  width: 100%;
  margin-bottom: var(--tp-space-4);
  border-radius: var(--tp-radius-md);
}

/* ── 图片展示区 ── */
.images-panel {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-bottom: var(--tp-space-4);
}

.images-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}

.images-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.images-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-brand-accent-bg);
  color: var(--tp-brand-accent);
}

.images-panel h3 {
  font-family: var(--tp-font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0;
}

/* 现代标签页样式 */
.modern-tabs {
  :deep(.el-tabs__header) {
    border-bottom: 1px solid var(--tp-border-light);
    margin-bottom: var(--tp-space-3);
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }

  :deep(.el-tabs__item) {
    font-family: var(--tp-font-heading);
    font-size: 13px;
    color: var(--tp-text-tertiary);
    padding: 0 16px;
    height: 38px;
    line-height: 38px;
    transition: all var(--tp-duration-normal);
    border-bottom: 2px solid transparent;
    margin-right: 4px;
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

.image-viewport {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  background: var(--tp-bg-sunken);
  border-radius: var(--tp-radius-md);
  overflow: hidden;
  border: 1px solid var(--tp-border-light);
}

.plot-img {
  max-width: 100%;
  max-height: 500px;
  object-fit: contain;
  cursor: zoom-in;
  transition: transform var(--tp-duration-slow);
}

.plot-img:hover {
  transform: scale(1.01);
}
</style>
