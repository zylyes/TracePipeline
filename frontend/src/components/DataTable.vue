<template>
  <div class="data-table">
    <el-tabs v-if="source === 'output'" v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="统计信息" name="统计信息" />
      <el-tab-pane label="裂隙情况" name="裂隙情况" />
      <el-tab-pane label="计算数据" name="计算数据" />
      <el-tab-pane label="原始端点" name="原始端点" />
      <el-tab-pane label="旋转端点" name="旋转端点" />
      <el-tab-pane label="走向与迹长" name="走向与迹长" />
      <el-tab-pane label="节点统计" name="节点统计" />
      <el-tab-pane label="节点明细" name="节点明细" />
      <el-tab-pane label="节点交点" name="节点交点" />
    </el-tabs>
    <div v-else class="source-hint">原始输入数据</div>

    <el-empty v-if="!loading && total === 0" description="该分区暂无数据" />
    <el-table v-else :data="tableData" size="small" stripe style="width: 100%" v-loading="loading">
      <el-table-column
        v-for="col in columns"
        :key="col"
        :prop="col"
        :label="col"
        sortable
        show-overflow-tooltip
      />
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next, sizes, total"
        :page-sizes="[10, 20, 50]"
        @change="loadData"
      />
      <el-input v-model="searchText" placeholder="搜索..." style="width:200px" size="small" clearable />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/pywebview'

const props = defineProps<{
  outcrop: string
  source?: string
}>()

const activeTab = ref('统计信息')
const tableData = ref<any[]>([])
const columns = ref<string[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const searchText = ref('')

// 前端分区名 -> 后端 section 参数 映射
const SECTION_MAP: Record<string, string> = {
  '统计信息': '基本信息',
  '裂隙情况': '裂隙情况',
  '计算数据': '计算数据',
  '原始端点': '原始坐标',
  '旋转端点': '旋转坐标',
  '走向与迹长': '走向与长度',
  '节点统计': '节点统计',
  '节点明细': '节点明细',
  '节点交点': '节点交点',
}

async function loadData() {
  if (!props.outcrop) return
  loading.value = true
  try {
    const src = props.source || 'output'
    const section = src === 'output' ? (SECTION_MAP[activeTab.value] || activeTab.value) : activeTab.value
    const res = await api.get_data(props.outcrop, section, page.value, pageSize.value, src)
    if (res.error) {
      ElMessage.error(res.error)
      tableData.value = []
      columns.value = []
      total.value = 0
      return
    }
    tableData.value = res.data || []
    columns.value = res.columns || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function handleTabChange() {
  page.value = 1
  loadData()
}

function exportCSV() {
  ElMessage.info('导出功能开发中')
}

function exportExcel() {
  ElMessage.info('导出功能开发中')
}

watch(() => props.outcrop, () => {
  page.value = 1
  loadData()
})

watch(() => props.source, () => {
  page.value = 1
  if (props.source === 'input') {
    activeTab.value = '原始输入'
  } else {
    activeTab.value = '统计信息'
  }
  loadData()
})

onMounted(() => {
  if (props.outcrop) {
    if (props.source === 'input') {
      activeTab.value = '原始输入'
    }
    loadData()
  }
})
</script>

<style scoped lang="scss">
.data-table {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.source-hint {
  padding: 8px 0;
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 12px;
}
.pagination-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}
</style>
