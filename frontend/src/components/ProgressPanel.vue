<template>
  <div class="progress-panel">
    <div class="control-bar">
      <el-button type="primary" :icon="VideoPlay" :loading="running" @click="emit('run')">
        {{ running ? '运行中...' : '一键运行' }}
      </el-button>
      <div class="parallel-control">
        <span>并行进程:</span>
        <el-slider v-model="parallel" :min="1" :max="maxParallel" style="width:160px;margin:0 8px;" />
        <span>{{ parallel }}/{{ maxParallel }}</span>
      </div>
    </div>
    <div class="progress-area">
      <el-progress :percentage="percentage" :stroke-width="18" :status="progressStatus" />
      <div class="current-file" v-if="progress.filename">
        当前: {{ progress.filename }} — {{ progress.message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'

const props = defineProps<{
  running: boolean
  progress: {
    current: number
    total: number
    filename: string
    message: string
  }
}>()

const emit = defineEmits<{
  (e: 'run'): void
}>()

// 根据 CPU 逻辑核心数动态设置上限（I/O 密集型任务允许略高于核心数）
const maxParallel = Math.max(4, Math.min((navigator.hardwareConcurrency || 4) * 2, 32))

const parallel = defineModel<number>('parallel', { default: 4 })

const percentage = computed(() => {
  if (!props.progress.total) return 0
  return Math.round((props.progress.current / props.progress.total) * 100)
})

const progressStatus = computed(() => {
  if (!props.running) return ''
  return 'success'
})
</script>

<style scoped lang="scss">
.progress-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-top: 16px;
}
.control-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}
.parallel-control {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #606266;
}
.current-file {
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}
</style>
