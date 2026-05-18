<template>
  <div class="data-table">
    <el-tabs v-if="source === 'output'" v-model="activeTab" @tab-change="handleTabChange" style="flex-shrink:0">
      <el-tab-pane label="裂隙情况" name="裂隙情况" />
      <el-tab-pane label="计算数据" name="计算数据" />
      <el-tab-pane label="原始端点" name="原始端点" />
      <el-tab-pane label="旋转端点" name="旋转端点" />
      <el-tab-pane label="走向与迹长" name="走向与迹长" />
      <el-tab-pane v-if="showNodeTabs !== false" label="节点统计" name="节点统计" />
      <el-tab-pane v-if="showNodeTabs !== false" label="节点明细" name="节点明细" />
      <el-tab-pane v-if="showNodeTabs !== false" label="节点交点" name="节点交点" />
    </el-tabs>
    <div v-else class="source-hint">原始输入数据</div>

    <div class="table-scroll" v-if="loading || total > 0">
      <el-table :data="tableData" size="small" stripe style="width: 100%; height: 100%" height="100%" v-loading="loading">
        <el-table-column
          v-for="col in columns"
          :key="col"
          :prop="col"
          :label="col"
          sortable
          show-overflow-tooltip
        />
      </el-table>
    </div>
    <el-empty v-else-if="!loading" description="该分区暂无数据" />

    <div class="pagination-bar" style="flex-shrink:0">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next, sizes, total"
        :page-sizes="[10, 20, 50]"
        @change="loadData"
      />
      <el-input v-model="searchText" placeholder="搜索..." style="width:200px" size="small" clearable @keyup.enter="onSearch" @clear="onSearch" />
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
  showNodeTabs?: boolean
}>()

const activeTab = ref('裂隙情况')
const tableData = ref<any[]>([])
const columns = ref<string[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const searchText = ref('')

function onSearch() {
  page.value = 1
  loadData()
}

// 前端分区名 -> 后端 section 参数 映射
const SECTION_MAP: Record<string, string> = {
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

watch(() => props.outcrop, () => {
  page.value = 1
  loadData()
}, { immediate: false })

  watch(() => props.source, () => {
    page.value = 1
    if (props.source === 'input') {
      activeTab.value = '原始输入'
    } else {
      activeTab.value = '裂隙情况'
    }
    loadData()
  })

onMounted(() => {
  if (props.outcrop) {
    if (props.source === 'input') {
      activeTab.value = '原始输入'
    } else {
      activeTab.value = '裂隙情况'
    }
    loadData()
  }
})
</script>

<style scoped lang="scss">
.data-table {
  background: var(--tp-bg-card);
  border-radius: var(--tp-radius-lg);
  padding: var(--tp-space-4);
  box-shadow: var(--tp-shadow-md);
  border: 1px solid var(--tp-border-light);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.source-hint {
  padding: var(--tp-space-2) 0;
  font-family: var(--tp-font-heading);
  font-size: 14px;
  font-weight: 500;
  color: var(--tp-text-secondary);
  border-bottom: 1px solid var(--tp-border-light);
  margin-bottom: var(--tp-space-3);
  flex-shrink: 0;
}
.table-scroll {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.pagination-bar {
  display: flex;
  align-items: center;
  gap: var(--tp-space-3);
  margin-top: var(--tp-space-3);
  flex-wrap: wrap;
  flex-shrink: 0;
}
</style>
