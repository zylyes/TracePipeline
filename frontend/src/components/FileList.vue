<template>
  <div class="file-list tp-card">
    <div class="file-list-header">
      <div class="file-list-header-left">
        <div class="file-list-icon">
          <el-icon :size="14"><Document /></el-icon>
        </div>
        <span class="file-list-title">文件列表</span>
      </div>
      <div class="file-list-actions">
        <el-checkbox v-model="selectAll" @change="toggleSelectAll" size="small">全选</el-checkbox>
        <el-button size="small" :icon="Refresh" @click="emit('refresh', true)">刷新</el-button>
        <span v-if="files.length === 0" class="empty-hint">暂无迹线表文件，请检查 input 目录</span>
      </div>
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
      :header-cell-style="headerCellStyle"
    >
      <el-table-column type="selection" width="40" reserve-selection />
      <el-table-column prop="stem" label="文件名" min-width="140" />
      <el-table-column prop="outcrop" label="露头" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small" effect="light" round>
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <template v-if="row.status === 'completed'">
            <el-button link size="small" type="primary" :icon="View" @click="emit('preview', row)">预览数据</el-button>
            <el-divider direction="vertical" />
            <el-button link size="small" type="success" :icon="Picture" @click="emit('open-image', row)">打开图片</el-button>
          </template>
          <el-button v-else link size="small" type="warning" :icon="VideoPlay" @click="emit('run', row)">处理</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Refresh, Document, View, Picture, VideoPlay } from '@element-plus/icons-vue'
import type { ElTable } from 'element-plus'
import type { TraceFile } from '@/types'

const props = defineProps<{
  files: TraceFile[]
}>()

const emit = defineEmits<{
  (e: 'refresh', force?: boolean): void
  (e: 'select', val: TraceFile[]): void
  (e: 'preview', row: TraceFile): void
  (e: 'open-image', row: TraceFile): void
  (e: 'run', row: TraceFile): void
}>()

const tableRef = ref<InstanceType<typeof ElTable>>()
const selectAll = ref(false)
const loading = ref(false)

const headerCellStyle = () => ({
  fontFamily: 'var(--tp-font-heading)',
  fontWeight: 600,
  background: 'var(--tp-bg-sunken)',
  color: 'var(--tp-text-primary)',
})

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
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-bottom: var(--tp-space-4);
}

.file-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
  flex-wrap: wrap;
  gap: var(--tp-space-2);
}

.file-list-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-list-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-info-bg);
  color: var(--tp-info);
}

.file-list-title {
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
}

.file-list-actions {
  display: flex;
  align-items: center;
  gap: var(--tp-space-2);
}

.empty-hint {
  color: var(--tp-text-muted);
  font-size: 14px;
  font-family: var(--tp-font-body);
}

:deep(.el-table) {
  --el-table-header-bg-color: var(--tp-bg-sunken);
  --el-table-row-hover-bg-color: var(--tp-bg-hover);
  --el-table-border-color: var(--tp-border-light);
}

:deep(.el-table th.el-table__cell) {
  font-family: var(--tp-font-heading);
  font-weight: 600;
  color: var(--tp-text-primary);
  background: var(--tp-bg-sunken);
}

:deep(.el-table .cell) {
  font-family: var(--tp-font-body);
  font-size: 13px;
}

:deep(.el-tag) {
  font-family: var(--tp-font-heading);
  font-weight: 500;
}

:deep(.el-button--link) {
  font-family: var(--tp-font-heading);
}
</style>
