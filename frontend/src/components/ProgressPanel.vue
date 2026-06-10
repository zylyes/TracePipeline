<template>
  <div class="progress-panel tp-card tp-neon-edge" :class="{ 'is-running': running, 'is-complete': !running && progress.total > 0 && progress.current >= progress.total }">
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
        :icon="VideoPlay"
        :loading="running"
        :disabled="running"
        @click="emit('run')"
        size="default"
        class="run-btn"
      >
        {{ running ? '运行中...' : '一键运行' }}
      </el-button>
      <div class="parallel-control">
        <span class="parallel-label">并行进程</span>
        <div class="slider-input-combo">
          <el-slider v-model="parallel" :min="1" :max="maxParallel" />
          <el-input-number v-model="parallel" :min="1" :max="maxParallel" :controls="false" size="small" style="width: 60px; flex-shrink: 0;" />
        </div>
        <span class="parallel-limit tp-data">上限 {{ maxParallel }}</span>
      </div>
    </div>
    <div class="progress-area">
      <div class="progress-meta">
        <span class="progress-chip">任务 {{ progress.current || 0 }} / {{ progress.total || 0 }}</span>
        <span class="progress-chip" :class="{ active: running }">{{ running ? '流水线运行中' : '等待任务' }}</span>
      </div>
      <el-progress
        :percentage="percentage"
        :stroke-width="8"
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

const parallel = defineModel<number>('parallel', { default: 1 })

// 数值变化时持久化到 localStorage（300ms 防抖）
let parallelDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(parallel, (val: number) => {
  if (parallelDebounceTimer) clearTimeout(parallelDebounceTimer)
  parallelDebounceTimer = setTimeout(() => {
    localStorage.setItem(STORAGE_KEY_PARALLEL, String(val))
  }, 300)
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
  return undefined
})

const progressColor = computed(() => {
  if (props.running) return 'var(--tp-brand-accent)'
  if (!props.running && props.progress.current > 0 && props.progress.current >= props.progress.total) {
    return 'var(--tp-success)'
  }
  return 'var(--tp-brand-primary)'
})
</script>

<style scoped lang="scss">
.progress-panel {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-top: var(--tp-space-4);
}

.progress-panel.is-running {
  box-shadow: var(--tp-shadow-md), var(--tp-glow-cyan-md);
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
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-info-bg);
  color: var(--tp-info);
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
  font-weight: 700;
  font-size: 14px;
  padding: 8px 22px;
  border-radius: var(--tp-radius-sm);
  letter-spacing: 0;
  background: linear-gradient(135deg, var(--tp-brand-accent), var(--tp-brand-accent-dark));
  border-color: var(--tp-brand-accent);
  color: var(--tp-text-inverse);
  box-shadow: var(--tp-brand-accent-shadow-sm);
  transition: all var(--tp-duration-normal) var(--tp-easing);
  position: relative;
  overflow: hidden;
}

.run-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%);
  transform: translateX(-100%);
  transition: transform 0.5s var(--tp-easing-expo);
}

.run-btn:hover::after {
  transform: translateX(100%);
}

.run-btn:hover,
.run-btn:focus {
  background: var(--tp-brand-accent-dark);
  border-color: var(--tp-brand-accent-dark);
  box-shadow: var(--tp-brand-accent-shadow-md);
  transform: translateY(-1px);
}

.run-btn:active {
  transform: translateY(0) scale(0.97);
  box-shadow: var(--tp-brand-accent-glow);
}

.parallel-control {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: var(--tp-text-secondary);
  background: rgba(238, 240, 244, 0.74);
  padding: 6px 12px;
  border-radius: var(--tp-radius-sm);
  border: 1px solid var(--tp-border-light);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.65);
}

.parallel-label {
  font-family: var(--tp-font-heading);
  font-weight: 500;
  font-size: 14px;
}

.parallel-limit {
  font-size: 13px;
  color: var(--tp-text-secondary);
}

.current-file {
  margin-top: var(--tp-space-2);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 22px;
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
  padding: 4px 10px;
  border-radius: var(--tp-radius-full);
  background: rgba(2, 132, 199, 0.08);
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.14);
}

.progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--tp-space-2);
  margin-bottom: var(--tp-space-2);
}

.progress-chip {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: var(--tp-radius-full);
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(125, 211, 252, 0.16);
  color: var(--tp-text-tertiary);
  font-family: var(--tp-font-data);
  font-size: 12px;
}

.progress-chip.active {
  color: var(--tp-brand-accent);
  background: rgba(2, 132, 199, 0.10);
  box-shadow: var(--tp-glow-cyan-sm);
}

.slider-input-combo {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 200px;
  margin: 0 8px;
}

.slider-input-combo .el-slider {
  flex: 1;
}

:deep(.el-slider__button) {
  width: 14px;
  height: 14px;
  transition: transform var(--tp-duration-normal) var(--tp-easing-expo);
}

:deep(.el-slider__button:hover) {
  transform: scale(1.35);
}

/* Element Plus 进度条样式覆盖 */
:deep(.modern-progress .el-progress-bar__outer) {
  border-radius: var(--tp-radius-full);
  background: rgba(26, 54, 93, 0.10);
  box-shadow: inset 0 1px 4px rgba(26, 54, 93, 0.14);
  overflow: hidden;
}

:deep(.modern-progress .el-progress-bar__inner) {
  position: relative;
  border-radius: var(--tp-radius-full);
  transition: width 0.4s var(--tp-easing-expo);
  background: linear-gradient(90deg, var(--tp-brand-accent-dark), var(--tp-brand-accent-light), var(--tp-geo-emerald)) !important;
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.42);
}

.is-running :deep(.modern-progress .el-progress-bar__inner::after) {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.42), transparent);
  animation: progressEnergySweep 1.3s linear infinite;
}

@keyframes progressEnergySweep {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(120%); }
}
</style>
