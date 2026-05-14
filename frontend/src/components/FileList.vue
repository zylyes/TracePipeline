<template>
  <div class="file-list">
    <div class="toolbar">
      <el-checkbox v-model="selectAll" @change="toggleSelectAll" size="small">全选</el-checkbox>
      <el-button size="small" :icon="Refresh" @click="emit('refresh')">刷新</el-button>
      <span v-if="files.length === 0" class="empty-hint">暂无迹线表文件，请检查 input 目录</span>
    </div>
    <el-table
      :data="files"
      size="small"
      style="width: 100%"
      @selection-change="handleSelectionChange"
      ref="tableRef"
      row-key="stem"
      v-loading="loading"
      empty-text="暂无数据"
    >
      <el-table-column type="selection" width="40" reserve-selection />
      <el-table-column prop="stem" label="文件名" min-width="140" />
      <el-table-column prop="outcrop" label="露头" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button v-if="row.status === 'completed'" link size="small" @click="emit('view', row)">查看</el-button>
          <el-button v-if="row.status === 'completed'" link size="small" @click="emit('preview', row)">预览数据</el-button>
          <el-button v-else link size="small" type="primary" @click="emit('run', row)">处理</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import type { ElTable } from 'element-plus'
import type { TraceFile } from '@/types'

const props = defineProps<{
  files: TraceFile[]
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'select', val: TraceFile[]): void
  (e: 'view', row: TraceFile): void
  (e: 'preview', row: TraceFile): void
  (e: 'run', row: TraceFile): void
}>()

const tableRef = ref<InstanceType<typeof ElTable>>()
const selectAll = ref(false)
const loading = ref(false)

function toggleSelectAll(val: boolean) {
  if (val) {
    tableRef.value?.toggleAllSelection()
  } else {
    tableRef.value?.clearSelection()
  }
}

function handleSelectionChange(val: TraceFile[]) {
  emit('select', val)
}

function statusType(status: string) {
  switch (status) {
    case 'completed': return 'success'
    case 'pending': return 'info'
    case 'error': return 'danger'
    default: return ''
  }
}

function statusLabel(status: string) {
  switch (status) {
    case 'completed': return '完成'
    case 'pending': return '待处理'
    case 'error': return '失败'
    default: return status
  }
}

watch(() => props.files, () => {
  selectAll.value = false
  nextTick(() => tableRef.value?.clearSelection())
}, { deep: true })
</script>

<style scoped lang="scss">
.file-list {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.empty-hint {
  color: #909399;
  font-size: 13px;
  margin-left: auto;
}
</style>
