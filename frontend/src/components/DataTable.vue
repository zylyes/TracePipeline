<template>
  <div class="data-table">
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="基本信息" name="基本信息" />
      <el-tab-pane label="原始坐标" name="原始坐标" />
      <el-tab-pane label="旋转坐标" name="旋转坐标" />
      <el-tab-pane label="走向与长度" name="走向与长度" />
    </el-tabs>

    <el-table :data="tableData" size="small" stripe style="width: 100%" v-loading="loading">
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
      <el-button size="small" @click="exportCSV">导出CSV</el-button>
      <el-button size="small" @click="exportExcel">导出Excel</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/pywebview'

const props = defineProps<{
  outcrop: string
}>()

const activeTab = ref('基本信息')
const tableData = ref<any[]>([])
const columns = ref<string[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const searchText = ref('')

async function loadData() {
  if (!props.outcrop) return
  loading.value = true
  try {
    const res = await api.get_data(props.outcrop, activeTab.value, page.value, pageSize.value)
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

onMounted(() => {
  if (props.outcrop) {
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
.pagination-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}
</style>
