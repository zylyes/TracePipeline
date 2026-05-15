<template>
  <div class="progress-panel">
    <div class="control-bar">
      <el-button type="primary" :icon="VideoPlay" :loading="running" @click="emit('run')">
        {{ running ? '运行中...' : '一键运行' }}
      </el-button>
      <div class="parallel-control">
        <span>并行进程:</span>
        <div class="slider-input-combo" style="width:220px;margin:0 8px;">
          <el-slider v-model="parallel" :min="1" :max="maxParallel" />
          <el-input-number v-model="parallel" :min="1" :max="maxParallel" :controls="false" size="small" style="width: 60px; flex-shrink: 0;" />
        </div>
        <span>上限 {{ maxParallel }}</span>
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
import { computed, onMounted, watch } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'

const STORAGE_KEY_PARALLEL = 'tp_last_parallel'

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

// 数值变化时持久化到 localStorage
watch(parallel, (val) => {
  localStorage.setItem(STORAGE_KEY_PARALLEL, String(val))
})

// 挂载时从 localStorage 恢复（上限受当前 maxParallel 限制）
onMounted(() => {
  const raw = localStorage.getItem(STORAGE_KEY_PARALLEL)
  if (raw !== null) {
    const saved = Number(raw)
    if (Number.isFinite(saved)) {
      const clamped = Math.max(1, Math.min(saved, maxParallel))
      if (clamped !== parallel.value) {
        parallel.value = clamped
      }
    }
  }
})

const percentage = computed(() => {
  if (!props.progress.total) return 0
  return Math.round((props.progress.current / props.progress.total) * 100)
})

const progressStatus = computed(() => {
  if (!props.running && props.progress.current > 0 && props.progress.current >= props.progress.total) {
    return 'success'
  }
  return undefined
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
.slider-input-combo {
  display: flex;
  align-items: center;
  gap: 12px;
}
.slider-input-combo .el-slider {
  flex: 1;
}
</style>
