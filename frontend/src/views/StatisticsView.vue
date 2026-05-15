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
    <div v-if="stats.nodes_summary" class="node-summary">
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="节点总数">{{ stats.nodes_summary.node_count }}</el-descriptions-item>
        <el-descriptions-item label="自由端点 I">{{ stats.nodes_summary.node_i_count }}</el-descriptions-item>
        <el-descriptions-item label="三叉节点 Y">{{ stats.nodes_summary.node_y_count }}</el-descriptions-item>
        <el-descriptions-item label="相交节点 X">{{ stats.nodes_summary.node_x_count }}</el-descriptions-item>
        <el-descriptions-item label="重叠节点">{{ stats.nodes_summary.node_overlap_count }}</el-descriptions-item>
        <el-descriptions-item label="多交汇点">{{ stats.nodes_summary.node_multi_count }}</el-descriptions-item>
        <el-descriptions-item label="交点事件数">{{ stats.nodes_summary.intersection_count }}</el-descriptions-item>
        <el-descriptions-item label="退化跳过">{{ stats.nodes_summary.degenerate_skipped }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="charts-row">
      <HistogramChart :histogram="stats.histogram || { bins: [], edges: [] }" />
      <PieChart :type-counts="{ type_i: stats.type_i || 0, type_ii: stats.type_ii || 0, type_iii: stats.type_iii || 0 }" />
    </div>

    <!-- 三图切换展示区 -->
    <div class="images-panel">
      <h3>处理结果图</h3>
      <el-tabs v-model="activeImageTab" type="border-card">
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

        <el-tab-pane label="走向玫瑰图" name="rose">
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
import { ref, onMounted } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import StatCards from '@/components/StatCards.vue'
import HistogramChart from '@/components/HistogramChart.vue'
import PieChart from '@/components/PieChart.vue'
import ImageViewer from '@/components/ImageViewer.vue'
import { api } from '@/api/pywebview'
import { loadImageBase64 } from '@/utils/image'

const outcrops = ref<string[]>([])
const selectedOutcrop = ref('')
const stats = ref<any>({})

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
  rawImageUrl.value = ''
  rotatedImageUrl.value = ''
  roseImageUrl.value = ''

  try {
    const res = await api.get_stats(selectedOutcrop.value)
    if (res.error) {
      ElMessage.error(res.error)
      return
    }
    stats.value = res

    // 扫描 output 目录获取图片路径
    const results = await api.get_results()
    const match = results.find((r: any) => r.outcrop === selectedOutcrop.value)
    if (match) {
      if (match.raw_plot) {
        rawImageUrl.value = await loadImageBase64(match.raw_plot)
      }
      if (match.rotated_plot) {
        rotatedImageUrl.value = await loadImageBase64(match.rotated_plot)
      }
      if (match.rose_plot) {
        roseImageUrl.value = await loadImageBase64(match.rose_plot)
      }
    }
  } catch (e) {
    ElMessage.error('加载统计失败')
  }
}

function openViewer(index: number) {
  const images = []
  if (rawImageUrl.value) images.push({ title: '原始迹线图', src: rawImageUrl.value })
  if (rotatedImageUrl.value) images.push({ title: '旋转迹线图', src: rotatedImageUrl.value })
  if (roseImageUrl.value) images.push({ title: '走向玫瑰图', src: roseImageUrl.value })
  viewerImages.value = images
  viewerInitialIndex.value = index
  viewerVisible.value = true
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
.images-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}
.images-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
.image-viewport {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}
.plot-img {
  max-width: 100%;
  max-height: 500px;
  object-fit: contain;
  cursor: zoom-in;
}
</style>
