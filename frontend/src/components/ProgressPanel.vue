<template>
  <div class="progress-panel tp-card">
    <div class="progress-header">
      <div class="progress-header-left">
        <div class="progress-header-icon">
          <el-icon :size="14"><VideoPlay /></el-icon>
        </div>
        <h3>进度控制</h3>
      </div>
    </div>
    <div class="control-bar">
      <el-button
        type="primary"
        :icon="VideoPlay"
        :loading="running"
        @click="emit('run')"
        size="default"
        class="run-btn"
      >
        {{ running ? '运行中...' : '一键运行' }}
      </el-button>
      <div class="parallel-control">
        <span class="parallel-label">并行进程:</span>
        <div class="slider-input-combo" style="width:220px;margin:0 8px;">
          <el-slider v-model="parallel" :min="1" :max="maxParallel" />
          <el-input-number v-model="parallel" :min="1" :max="maxParallel" :controls="false" size="small" style="width: 60px; flex-shrink: 0;" />
        </div>
        <span class="parallel-limit tp-data">上限 {{ maxParallel }}</span>
      </div>
    </div>
    <div class="progress-area">
      <el-progress
        :percentage="percentage"
        :stroke-width="14"
        :status="progressStatus"
        :color="progressColor"
        class="modern-progress"
      />
      <div class="current-file">
        <span v-if="!running && progress.total > 0 && progress.current >= progress.total" class="complete-text">
          <el-icon :size="14"><CircleCheck /></el-icon>
          全部处理完成
        </span>
        <span v-else-if="!running && progress.current === 0 && progress.total === 0" class="idle-text">未处理</span>
        <span v-else-if="progress.filename" class="running-text">
          <el-icon class="tp-rotate" :size="12"><Loading /></el-icon>
          当前: {{ progress.filename }} — {{ progress.message }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { VideoPlay, CircleCheck, Loading } from '@element-plus/icons-vue'

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

const progressColor = computed(() => {
  if (props.running) return 'var(--tp-brand-accent)'
  return 'var(--tp-brand-primary)'
})
</script>

<style scoped lang="scss">
.progress-panel {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-top: var(--tp-space-4);
}

.progress-header {
  display: flex;
  align-items: center;
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}

.progress-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--tp-radius-sm);
  background: var(--tp-success-bg);
  color: var(--tp-success);
}

.progress-panel h3 {
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0;
}

.control-bar {
  display: flex;
  align-items: center;
  gap: var(--tp-space-4);
  margin-bottom: var(--tp-space-3);
  flex-wrap: wrap;
}

.run-btn {
  font-family: var(--tp-font-heading);
  font-weight: 500;
}

.parallel-control {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: var(--tp-text-secondary);
}

.parallel-label {
  font-family: var(--tp-font-heading);
  font-weight: 500;
}

.parallel-limit {
  font-size: 12px;
  color: var(--tp-text-muted);
}

.current-file {
  margin-top: var(--tp-space-3);
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.complete-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tp-success);
  font-weight: 500;
}

.idle-text {
  color: var(--tp-text-muted);
}

.running-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tp-brand-accent);
}

.slider-input-combo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-input-combo .el-slider {
  flex: 1;
}

/* Element Plus 进度条样式覆盖 */
:deep(.modern-progress .el-progress-bar__outer) {
  border-radius: var(--tp-radius-full);
  background: var(--tp-bg-sunken);
}

:deep(.modern-progress .el-progress-bar__inner) {
  border-radius: var(--tp-radius-full);
  transition: width 0.4s var(--tp-easing-expo);
}

:deep(.modern-progress.el-progress--success .el-progress-bar__inner) {
  background: var(--tp-success);
}
</style>
